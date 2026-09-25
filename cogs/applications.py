import asyncio
import json
import re
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

from database import execute, fetch_one, fetch_all, get_setting, set_setting

GUILD_ID = 880440495233454080
LOG_CHANNEL_ID = 1386771246733066433

RECRUIT_ROLE_ID = 1405605410018295989
TEMP_CALL_ROLE_ID = 1307538910964093020

APP_TAG = "FAMU_APP"

SET_ACCEPT_ROLES_KEY = "app_accept_roles"
SET_REJECT_ROLES_KEY = "app_reject_remove_roles"
SET_APPS_PING_ROLE_KEY = "applications_ping_role_id"
SET_APPS_LOG_CHANNEL_KEY = "applications_log_channel_id"
SET_APPS_TEMP_ROLE_KEY = "applications_temp_role_id"
SET_APPS_QUESTIONS_KEY = "application_questions"
SET_APPS_POLL_CURSOR_KEY = "apps_poll_cursor"

DEFAULT_QUESTIONS = [
    {"id": "nickname", "label": "Игровой никнейм", "required": True},
    {"id": "age", "label": "Возраст", "required": True},
    {"id": "experience", "label": "Опыт в игре", "required": True},
    {"id": "reason", "label": "Почему хотите вступить", "required": True, "min": 20},
]

PANEL_API_URL = "https://melancholia-api.sasha75077.workers.dev"


def _panel_key():
    import os
    return os.getenv("PANEL_SYNC_SECRET", "")


def _api_req(method, path, payload=None):
    key = _panel_key()
    if not key:
        return None
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        PANEL_API_URL + path,
        data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}",
                 "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


async def panel_role_of(guild_id: str, user_id: str) -> str:
    row = await fetch_one(
        "SELECT role FROM permissions WHERE guild_id = ? AND discord_id = ?",
        (str(guild_id), str(user_id)),
    )
    return (row or {}).get("role") or "user"


async def is_staff_member(member: discord.Member) -> bool:
    if is_admin(member):
        return True
    return (await panel_role_of(str(member.guild.id), str(member.id))) in ("admin", "recruiter", "owner")


async def find_guild_for_channel(bot, channel_id: int):
    for g in list(bot.guilds):
        try:
            if g.get_channel(int(channel_id)):
                return g
        except Exception:
            pass
    return None


async def recruiter_pings(guild_id: str) -> str | None:
    try:
        raw = await get_setting("panel_recruiter_role_ids", str(guild_id)) or ""
        ids = [x.strip() for x in raw.split(",") if x.strip().isdigit()]
        return " ".join(f"<@&{i}>" for i in ids) or None
    except Exception:
        return None


async def get_log_channel(guild: discord.Guild):
    raw = None
    try:
        raw = parse_single_id(await get_setting(SET_APPS_LOG_CHANNEL_KEY, str(guild.id)))
    except Exception:
        raw = None
    cid = raw or (LOG_CHANNEL_ID if guild.id == GUILD_ID else None)
    if not cid:
        return None
    ch = guild.get_channel(cid)
    if ch is None:
        try:
            ch = await guild.fetch_channel(cid)
        except Exception:
            return None
    return ch


async def get_temp_role(guild: discord.Guild):
    raw = None
    try:
        raw = parse_single_id(await get_setting(SET_APPS_TEMP_ROLE_KEY, str(guild.id)))
    except Exception:
        raw = None
    rid = raw or TEMP_CALL_ROLE_ID
    return guild.get_role(rid)


async def get_questions(guild_id: str) -> list:
    try:
        raw = await get_setting(SET_APPS_QUESTIONS_KEY, str(guild_id))
        if raw:
            parsed = json.loads(raw)
            if isinstance(parsed, list) and parsed:
                return [q for q in parsed if isinstance(q, dict) and q.get("id") and q.get("label")][:5]
    except Exception:
        pass
    return DEFAULT_QUESTIONS


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_admin(m: discord.Member) -> bool:
    return m.guild_permissions.administrator


def extract_app_id(embed: discord.Embed) -> str | None:
    if not embed.footer or not embed.footer.text:
        return None
    if APP_TAG not in embed.footer.text:
        return None
    m = re.search(r"app_id=([a-f0-9\-]{10,})", embed.footer.text, re.I)
    return m.group(1) if m else None


def extract_candidate_id(embed: discord.Embed) -> int | None:
    for f in embed.fields:
        if f.name == "Discord":
            mm = re.search(r"(\d{10,})", f.value)
            if mm:
                return int(mm.group(1))
    return None


def parse_id_list(s: str | None) -> list[int]:
    if not s:
        return []
    out: list[int] = []
    for part in s.split(","):
        part = part.strip()
        if part.isdigit():
            out.append(int(part))
    return out


def parse_single_id(s: str | None) -> int | None:
    if not s:
        return None
    s = s.strip()
    return int(s) if s.isdigit() else None


def find_app_embed(embeds: list[discord.Embed]) -> tuple[discord.Embed | None, str | None, int | None]:
    app_id = None
    cand_id = None
    chosen = None

    for e in embeds:
        a = extract_app_id(e)
        c = extract_candidate_id(e)
        if a and c:
            return e, a, c

        if chosen is None and a:
            chosen = e
        app_id = app_id or a
        cand_id = cand_id or c

    return chosen, app_id, cand_id


async def safe_dm(user: discord.abc.User, text: str) -> bool:
    try:
        await user.send(text)
        return True
    except:
        return False


async def fetch_member_safe(guild: discord.Guild, user_id: int) -> discord.Member | None:
    member = guild.get_member(user_id)
    if member is None:
        try:
            member = await guild.fetch_member(user_id)
        except discord.NotFound:
            return None
    return member


def _parse_ts(s):
    if not s:
        return None
    t = str(s).strip().replace('Z', '+00:00')
    try:
        dt = datetime.fromisoformat(t)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class RejectReasonModal(discord.ui.Modal, title="Причина отказа"):
    reason = discord.ui.TextInput(label="Причина", style=discord.TextStyle.paragraph, max_length=500)

    def __init__(self, cog: "ApplicationsCog", app_id: str):
        super().__init__()
        self.cog = cog
        self.app_id = app_id

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        m = await interaction.followup.send("⏳ Обрабатываю...", ephemeral=True, wait=True)
        ok, msg = await self.cog.decide(self.app_id, interaction, accepted=False, reason=str(self.reason))
        await m.edit(content=msg)


class ApplicationModal(discord.ui.Modal):
    def __init__(self, cog: "ApplicationsCog", guild_id: int, questions: list):
        super().__init__(title="Заявка на вступление")
        self.cog = cog
        self.guild_id = str(guild_id)
        self.questions = (questions or [])[:5]
        self.inputs: list = []
        for i, q in enumerate(self.questions):
            style = discord.TextStyle.short if i < 2 else discord.TextStyle.paragraph
            inp = discord.ui.TextInput(
                label=str(q.get("label") or q.get("id"))[:45],
                style=style,
                required=bool(q.get("required")),
                max_length=1000,
                placeholder=(f"Минимум {q['min']} символов" if q.get("min") else None),
            )
            self.add_item(inp)
            self.inputs.append((q, inp))

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None:
            return await interaction.response.send_message("❌ Только на сервере.", ephemeral=True)
        try:
            fam_raw = await get_setting("family_member_role_ids", str(guild.id)) or ""
            fam_ids = {x.strip() for x in fam_raw.split(",") if x.strip().isdigit()}
            if fam_ids and isinstance(interaction.user, discord.Member):
                if any(str(r.id) in fam_ids for r in interaction.user.roles):
                    return await interaction.response.send_message(
                        "❌ Ты уже состоишь в семье — заявка не нужна.", ephemeral=True)
        except Exception:
            pass
        answers: dict = {}
        for q, inp in self.inputs:
            v = (inp.value or "").strip()
            if q.get("required") and not v:
                return await interaction.response.send_message(f"❌ Заполни: {q.get('label')}", ephemeral=True)
            if q.get("min") and len(v) < int(q["min"]):
                return await interaction.response.send_message(
                    f"❌ «{q.get('label')}» минимум {q['min']} символов", ephemeral=True)
            answers[str(q.get("id"))] = v
        dup = await fetch_one(
            "SELECT id FROM applications WHERE guild_id=? AND discord_user_id=? AND status IN ('PENDING','CLAIMED','ACCEPTED') LIMIT 1",
            (str(guild.id), str(interaction.user.id)),
        )
        if dup:
            return await interaction.response.send_message("❌ У тебя уже есть открытая или принятая заявка.", ephemeral=True)
        # + проверка сайта (там может висеть несинкнутая)
        try:
            import urllib.request as _u, json as _j, os as _o
            _key = _o.getenv("PANEL_SYNC_SECRET", "")
            _api = _o.getenv("PANEL_API_URL", "https://melancholia-api.sasha75077.workers.dev").rstrip("/")
            if _key:
                _req = _u.Request(
                    f"{_api}/guilds/{guild.id}/applications/open?discord_id={interaction.user.id}",
                    headers={"Authorization": f"Bearer {_key}",
                             "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                    method="GET")
                with _u.urlopen(_req, timeout=10) as _r:
                    _d = _j.loads(_r.read().decode("utf-8"))
                if (_d or {}).get("open"):
                    return await interaction.response.send_message("❌ У тебя уже есть открытая заявка (на сайте).", ephemeral=True)
        except Exception as e:
            print(f"[ApplicationsCog] site dup check warn: {e}")
        app_id = str(uuid.uuid4())
        await execute(
            "INSERT INTO applications (id, discord_user_id, guild_id, created_at, status, answers) VALUES (?, ?, ?, ?, 'PENDING', ?)",
            (app_id, str(interaction.user.id), str(guild.id), now_iso(), json.dumps(answers, ensure_ascii=False)),
        )
        ch = await get_log_channel(guild)
        if ch is None:
            return await interaction.response.send_message("❌ Канал заявок не настроен.", ephemeral=True)
        embed = discord.Embed(title="📨 Заявка в семью", color=0x3498DB)
        for q in self.questions:
            v = answers.get(str(q.get("id")), "") or "—"
            embed.add_field(name=str(q.get("label"))[:256], value=v[:1024], inline=False)
        embed.add_field(name="Discord", value=f"<@{interaction.user.id}>", inline=False)
        embed.set_footer(text=f"{APP_TAG} app_id={app_id}")
        pings = await recruiter_pings(str(guild.id))
        panel_msg = await ch.send(content=pings, embed=embed, view=ApplicationView(self.cog, app_id))
        await execute(
            "UPDATE applications SET log_channel_id=?, log_message_id=? WHERE id=?",
            (str(ch.id), str(panel_msg.id), app_id),
        )
        try:
            from services.api_sync import queue_application_sync
            queue_application_sync(str(guild.id), app_id, str(interaction.user.id), "PENDING",
                                   log_channel_id=str(ch.id), log_message_id=str(panel_msg.id),
                                   answers=answers)
        except Exception as e:
            print(f"[api_sync] warn: {e}")
        try:
            await interaction.user.send("✅ Заявка отправлена! Ответ придет сюда.")
        except Exception:
            pass
        await interaction.response.send_message("✅ Заявка отправлена!", ephemeral=True)


class ApplicationView(discord.ui.View):
    def __init__(self, cog: "ApplicationsCog", app_id: str):
        super().__init__(timeout=None)
        self.cog = cog
        self.app_id = app_id

    def allowed(self, member: discord.Member) -> bool:
        # Синхронный быстрый чек; точная проверка прав - в хендлере кнопки
        return is_admin(member)

    def _resolve_app_id(self, interaction: discord.Interaction) -> str | None:
        if self.app_id != "placeholder":
            return self.app_id
        if interaction.message and interaction.message.embeds:
            _, app_id, _ = find_app_embed(interaction.message.embeds)
            return app_id
        return None

    @discord.ui.button(label="Взять", style=discord.ButtonStyle.primary, custom_id="app:claim")
    async def claim_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("❌ Только на сервере.", ephemeral=True)
        if not self.allowed(interaction.user) and not await is_staff_member(interaction.user):
            return await interaction.response.send_message("❌ Нет доступа.", ephemeral=True)

        app_id = self._resolve_app_id(interaction)
        if not app_id:
            return await interaction.response.send_message("❌ Не удалось найти заявку.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        m = await interaction.followup.send("⏳ Обрабатываю...", ephemeral=True, wait=True)
        ok, msg = await self.cog.claim(app_id, interaction)
        await m.edit(content=msg)

    @discord.ui.button(label="✅ Принять", style=discord.ButtonStyle.success, custom_id="app:accept")
    async def accept_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("❌ Только на сервере.", ephemeral=True)
        prole = await panel_role_of(str(interaction.guild.id), str(interaction.user.id))
        if not is_admin(interaction.user) and prole not in ("admin", "owner"):
            return await interaction.response.send_message("❌ Только админ.", ephemeral=True)

        app_id = self._resolve_app_id(interaction)
        if not app_id:
            return await interaction.response.send_message("❌ Не удалось найти заявку.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        m = await interaction.followup.send("⏳ Обрабатываю...", ephemeral=True, wait=True)
        ok, msg = await self.cog.decide(app_id, interaction, accepted=True, reason=None)
        await m.edit(content=msg)

    @discord.ui.button(label="❌ Отклонить", style=discord.ButtonStyle.danger, custom_id="app:reject")
    async def reject_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("❌ Только на сервере.", ephemeral=True)
        prole = await panel_role_of(str(interaction.guild.id), str(interaction.user.id))
        if not is_admin(interaction.user) and prole not in ("admin", "owner"):
            return await interaction.response.send_message("❌ Только админ.", ephemeral=True)

        app_id = self._resolve_app_id(interaction)
        if not app_id:
            return await interaction.response.send_message("❌ Не удалось найти заявку.", ephemeral=True)

        await interaction.response.send_modal(RejectReasonModal(self.cog, app_id))


class ApplicationsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._did_rescan = False

    async def ensure_tables(self):
        await execute(
            "CREATE TABLE IF NOT EXISTS applications ("
            "id TEXT PRIMARY KEY, "
            "discord_user_id TEXT NOT NULL, "
            "created_at TEXT NOT NULL, "
            "status TEXT NOT NULL DEFAULT 'PENDING', "
            "claimed_by TEXT, claimed_at TEXT, "
            "decided_by TEXT, decided_at TEXT, decision_reason TEXT, "
            "log_channel_id TEXT NOT NULL, log_message_id TEXT NOT NULL, "
            "thread_id TEXT, "
            "temp_role_given INTEGER NOT NULL DEFAULT 0"
            ")",
            (),
        )

    @commands.Cog.listener()
    async def on_ready(self):
        await self.ensure_tables()

        self.bot.add_view(ApplicationView(self, "placeholder"))

        if not self.site_poll_loop.is_running():
            self.site_poll_loop.start()

        if not self.nudge_loop.is_running():
            self.nudge_loop.start()

        if not self._did_rescan:
            self._did_rescan = True
            try:
                await self.rescan_last_apps(limit=20, debug=False)
            except Exception as e:
                print("[ApplicationsCog] rescan failed:", repr(e))

        print("[ApplicationsCog] ready")

    async def rescan_last_apps(self, limit: int = 20, debug: bool = False):
        for guild in list(self.bot.guilds):
            try:
                await self._rescan_guild(guild, limit=limit, debug=debug)
            except Exception as e:
                print("[ApplicationsCog] rescan failed:", repr(e))

    async def _rescan_guild(self, guild: discord.Guild, limit: int = 20, debug: bool = False):
        ch = await get_log_channel(guild)
        if ch is None:
            return

        async for msg in ch.history(limit=limit, oldest_first=False):
            if not msg.embeds:
                continue

            emb, app_id, cand_id = find_app_embed(msg.embeds)
            if not emb or not app_id or not cand_id:
                continue

            row = await fetch_one("SELECT id FROM applications WHERE id=?", (app_id,))
            if row:
                continue

            is_panel = False
            try:
                is_panel = (self.bot.user is not None and msg.author.id == self.bot.user.id and bool(msg.components))
            except:
                is_panel = (self.bot.user is not None and msg.author.id == self.bot.user.id)

            if is_panel:
                await execute(
                    "INSERT OR REPLACE INTO applications (id, discord_user_id, created_at, status, log_channel_id, log_message_id) "
                    "VALUES (?, ?, ?, 'PENDING', ?, ?)",
                    (app_id, str(cand_id), now_iso(), str(ch.id), str(msg.id)),
                )
                try:
                    from services.api_sync import queue_application_sync
                    queue_application_sync(str(ch.guild.id), app_id, str(cand_id), "PENDING",
                                           log_channel_id=str(ch.id), log_message_id=str(msg.id))
                except Exception as e:
                    print(f"[api_sync] warn: {e}")
                await self.refresh_message(app_id)
                continue

            if msg.webhook_id is not None:
                ping_role_id = parse_single_id(await get_setting(SET_APPS_PING_ROLE_KEY))
                content = f"<@&{ping_role_id}>" if ping_role_id else None

                panel_msg = await ch.send(
                    content=content,
                    embed=emb,
                    view=ApplicationView(self, app_id),
                    allowed_mentions=discord.AllowedMentions(roles=True) if ping_role_id else discord.AllowedMentions.none(),
                )

                await execute(
                    "INSERT OR REPLACE INTO applications (id, discord_user_id, created_at, status, log_channel_id, log_message_id) "
                    "VALUES (?, ?, ?, 'PENDING', ?, ?)",
                    (app_id, str(cand_id), now_iso(), str(ch.id), str(panel_msg.id)),
                )
                try:
                    from services.api_sync import queue_application_sync
                    queue_application_sync(str(ch.guild.id), app_id, str(cand_id), "PENDING",
                                           log_channel_id=str(ch.id), log_message_id=str(panel_msg.id))
                except Exception as e:
                    print(f"[api_sync] warn: {e}")

                await self.refresh_message(app_id)

                try:
                    await msg.delete()
                except:
                    pass

    async def _set_claim_author(self, embed: discord.Embed, guild: discord.Guild, claimed_by: str | None):
        if not claimed_by:
            try:
                embed.remove_author()
            except:
                pass
            return

        try:
            m = guild.get_member(int(claimed_by)) or await guild.fetch_member(int(claimed_by))
            embed.set_author(name=f"Взял: {m.display_name}", icon_url=m.display_avatar.url)
        except:
            embed.set_author(name=f"Взял: {claimed_by}")

    async def close_thread_for_app(self, guild: discord.Guild, app_id: str, note: str):
        row = await fetch_one("SELECT thread_id, log_channel_id FROM applications WHERE id=?", (app_id,))
        if not row or not row.get("thread_id"):
            return

        thread_id = int(row["thread_id"])
        thread = guild.get_thread(thread_id)

        if thread is None:
            try:
                ch = guild.get_channel(int(row["log_channel_id"])) or await guild.fetch_channel(int(row["log_channel_id"]))
                thread = await ch.fetch_channel(thread_id)
            except:
                thread = None

        if thread is None:
            return

        try:
            await thread.send(note[:1800])
        except:
            pass

        try:
            await thread.edit(archived=True, locked=True, reason=f"Заявка {app_id} закрыта")
            return
        except:
            pass

        try:
            await thread.edit(locked=True, reason=f"Заявка {app_id} закрыта")
        except:
            pass
        try:
            await thread.edit(archived=True, reason=f"Заявка {app_id} закрыта")
        except:
            pass

    async def refresh_message(self, app_id: str, remove_buttons: bool = False, color: discord.Color | None = None):
        row = await fetch_one("SELECT * FROM applications WHERE id=?", (app_id,))
        if not row:
            return

        guild = await find_guild_for_channel(self.bot, int(row["log_channel_id"]))
        if guild is None:
            guild = self.bot.get_guild(GUILD_ID) or await self.bot.fetch_guild(GUILD_ID)
        ch = guild.get_channel(int(row["log_channel_id"])) or await guild.fetch_channel(int(row["log_channel_id"]))
        msg = await ch.fetch_message(int(row["log_message_id"]))

        embed = msg.embeds[0] if msg.embeds else discord.Embed(title="📨 Заявка в семью")
        if color:
            embed.color = color

        status = row["status"]
        claimed_by = row.get("claimed_by")
        decided_by = row.get("decided_by")

        await self._set_claim_author(embed, guild, claimed_by)

        old_fields = [f for f in embed.fields if f.name != "Статус"]
        embed.clear_fields()

        extra = status
        if claimed_by:
            extra += f"\nВзял: <@{claimed_by}>"
        if decided_by:
            extra += f"\nРешение: <@{decided_by}>"
            if row.get("decision_reason"):
                extra += f"\nПричина: {row['decision_reason']}"

        thread_id = row.get("thread_id")
        if thread_id:
            extra += f"\nЧат: <#{thread_id}>"

        embed.add_field(name="Статус", value=extra[:1024], inline=False)
        for f in old_fields:
            embed.add_field(name=f.name, value=f.value, inline=f.inline)

        if remove_buttons:
            await msg.edit(embed=embed, view=None)
        else:
            view = ApplicationView(self, app_id)
            if not claimed_by:
                # Кнопки решения только после взятия
                for child in [ch for ch in list(view.children)
                              if getattr(ch, "custom_id", "") in ("app:accept", "app:reject")]:
                    view.remove_item(child)
            await msg.edit(embed=embed, view=view)

    async def claim(self, app_id: str, interaction: discord.Interaction):
        row = await fetch_one("SELECT * FROM applications WHERE id=?", (app_id,))
        if not row:
            return False, "❌ Не нашёл заявку в БД."
        if row["status"] in ("ACCEPTED", "REJECTED"):
            return False, "❌ Заявка уже закрыта."

        # Перехват разрешен: взять чужую может любой стафф
        took_over = bool(row.get("claimed_by")) and str(row.get("claimed_by")) != str(interaction.user.id)

        guild = interaction.guild
        recruiter: discord.Member = interaction.user  # type: ignore

        cand_id = int(row["discord_user_id"])
        member = await fetch_member_safe(guild, cand_id)

        # Если кандидат покинул сервер — сразу отклоняем
        if member is None:
            await execute(
                "UPDATE applications SET status='REJECTED', decided_by=?, decided_at=?, decision_reason=? WHERE id=?",
                (str(recruiter.id), now_iso(), "Кандидат покинул сервер", app_id),
            )
            try:
                from services.api_sync import queue_application_sync
                queue_application_sync(str(guild.id), app_id, str(cand_id), "REJECTED", "Кандидат покинул сервер",
                                       decided_by=str(recruiter.id))
            except Exception as e:
                print(f"[api_sync] warn: {e}")
            await self.refresh_message(
                app_id,
                remove_buttons=True,
                color=discord.Color.red(),
            )
            await self.close_thread_for_app(guild, app_id, note="🔒 Заявка отклонена автоматически — кандидат покинул сервер.")
            return False, "❌ Кандидат покинул сервер. Заявка автоматически отклонена."

        await execute(
            "UPDATE applications SET status='CLAIMED', claimed_by=?, claimed_at=?, nudged_at=NULL WHERE id=?",
            (str(recruiter.id), now_iso(), app_id),
        )
        try:
            from services.api_sync import queue_application_sync
            queue_application_sync(str(guild.id), app_id, str(cand_id), "CLAIMED",
                                   claimed_by=str(recruiter.id))
        except Exception as e:
            print(f"[api_sync] warn: {e}")

        temp_role = await get_temp_role(guild)
        if temp_role and temp_role not in member.roles:
            await member.add_roles(temp_role, reason="Заявка взята на рассмотрение (обзвон)")
            await execute("UPDATE applications SET temp_role_given=1 WHERE id=?", (app_id,))

        thread = None
        try:
            row2 = await fetch_one("SELECT thread_id FROM applications WHERE id=?", (app_id,))
            thread_id = (row2.get("thread_id") if row2 else None)

            if thread_id:
                thread = guild.get_thread(int(thread_id))

            if thread is None:
                base_msg = interaction.message
                thread = await base_msg.create_thread(
                    name=f"Заявка {app_id[:8]} • {member.display_name}",
                    auto_archive_duration=1440,
                    reason=f"Чат по заявке {app_id}",
                )
                await execute("UPDATE applications SET thread_id=? WHERE id=?", (str(thread.id), app_id))
                try:
                    from services.api_sync import queue_application_sync
                    queue_application_sync(str(guild.id), app_id, str(cand_id), "CLAIMED",
                                           claimed_by=str(recruiter.id), thread_id=str(thread.id))
                except Exception as e:
                    print(f"[api_sync] warn: {e}")

                await thread.send(
                    "🗣️ Чат по заявке создан.\n"
                    f"Кандидат: <@{member.id}>\n"
                    f"Рекрутер: <@{recruiter.id}>\n\n"
                    "Рекрутер пишет сюда, кандидат отвечает боту в ЛС."
                )
        except Exception as e:
            print("[ApplicationsCog] thread create failed:", repr(e))

        dm_ok = await safe_dm(member, "Твою заявку взяли на рассмотрение. Пиши сюда (в ЛС боту) — я передам рекрутеру.")
        await self.refresh_message(app_id)

        msg = "✅ Взято."
        if thread:
            msg += f" Чат: <#{thread.id}>."
        if not dm_ok:
            msg += " ⚠️ Не смог написать кандидату в ЛС (закрыты DM)."
        return True, msg

    async def decide(self, app_id: str, interaction: discord.Interaction, accepted: bool, reason: str | None):
        row = await fetch_one("SELECT * FROM applications WHERE id=?", (app_id,))
        if not row:
            return False, "❌ Не нашёл заявку."
        if row["status"] in ("ACCEPTED", "REJECTED"):
            return False, "❌ Уже закрыта."

        if row.get("claimed_by") and int(row["claimed_by"]) != interaction.user.id and not is_admin(interaction.user):
            return False, f"❌ Эту заявку рассматривает <@{row['claimed_by']}>. Только он (или админ Discord) может принять/отклонить."

        guild = interaction.guild
        cand_id = int(row["discord_user_id"])
        member = await fetch_member_safe(guild, cand_id)

        # Если кандидат покинул сервер — автоматически отклоняем
        if member is None:
            await execute(
                "UPDATE applications SET status='REJECTED', decided_by=?, decided_at=?, decision_reason=? WHERE id=?",
                (str(interaction.user.id), now_iso(), "Кандидат покинул сервер", app_id),
            )
            try:
                from services.api_sync import queue_application_sync
                queue_application_sync(str(guild.id), app_id, str(cand_id), "REJECTED", "Кандидат покинул сервер",
                                       decided_by=str(interaction.user.id))
            except Exception as e:
                print(f"[api_sync] warn: {e}")
            await self.refresh_message(
                app_id,
                remove_buttons=True,
                color=discord.Color.red(),
            )
            await self.close_thread_for_app(guild, app_id, note="🔒 Заявка отклонена автоматически — кандидат покинул сервер.")
            return False, "❌ Кандидат покинул сервер. Заявка автоматически отклонена."

        new_status = "ACCEPTED" if accepted else "REJECTED"
        await execute(
            "UPDATE applications SET status=?, decided_by=?, decided_at=?, decision_reason=? WHERE id=?",
            (new_status, str(interaction.user.id), now_iso(), reason, app_id),
        )
        try:
            from services.api_sync import queue_application_sync
            queue_application_sync(str(guild.id), app_id, str(cand_id), new_status, reason,
                                   decided_by=str(interaction.user.id))
        except Exception as e:
            print(f"[api_sync] warn: {e}")

        temp_role = await get_temp_role(guild)
        if temp_role and temp_role in member.roles:
            await member.remove_roles(temp_role, reason="Заявка закрыта")
            await execute("UPDATE applications SET temp_role_given=0 WHERE id=?", (app_id,))

        if accepted:
            accept_raw = await get_setting(SET_ACCEPT_ROLES_KEY, str(guild.id)) or await get_setting(SET_ACCEPT_ROLES_KEY)
            role_ids = parse_id_list(accept_raw)
            roles = [guild.get_role(rid) for rid in role_ids]
            roles = [r for r in roles if r is not None]
            if roles:
                try:
                    await member.add_roles(*roles, reason=f"Заявка {app_id} принята")
                except discord.Forbidden:
                    try:
                        from services.role_sync import bot_log
                        await bot_log(self.bot, str(guild.id),
                                      f"Нет прав выдать роли заявки {member} ({member.id}). Проверь иерархию ролей и Manage Roles.")
                    except Exception:
                        pass
        else:
            reject_raw = await get_setting(SET_REJECT_ROLES_KEY, str(guild.id)) or await get_setting(SET_REJECT_ROLES_KEY)
            remove_ids = parse_id_list(reject_raw)
            roles = [guild.get_role(rid) for rid in remove_ids]
            roles = [r for r in roles if r is not None and r in member.roles]
            if roles:
                try:
                    await member.remove_roles(*roles, reason=f"Заявка {app_id} отклонена")
                except discord.Forbidden:
                    pass

        await self.refresh_message(
            app_id,
            remove_buttons=True,
            color=(discord.Color.green() if accepted else discord.Color.red()),
        )

        try:
            short = app_id[:8]
            if accepted:
                await member.send(f"✅ Твоя заявка ({short}) принята!")
            else:
                await member.send(f"❌ Твоя заявка ({short}) отклонена. Причина: {reason or '—'}")
        except:
            pass

        status_text = "принята" if accepted else "отклонена"
        await self.close_thread_for_app(guild, app_id, note=f"🔒 Заявка {status_text}. Thread закрыт.")

        return True, ("✅ Принято." if accepted else "✅ Отклонено.")

    @app_commands.command(name="заявка", description="Подать заявку на вступление в семью")
    async def apply_cmd(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Только на сервере.", ephemeral=True)
        questions = await get_questions(str(interaction.guild.id))
        await interaction.response.send_modal(ApplicationModal(self, interaction.guild.id, questions))

    @tasks.loop(seconds=60)
    async def site_poll_loop(self):
        for guild in list(self.bot.guilds):
            try:
                await self._poll_guild(guild)
            except Exception as e:
                print(f"[ApplicationsCog] poll warn {guild.id}: {e}")

    @site_poll_loop.before_loop
    async def _before_poll(self):
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=10)
    async def nudge_loop(self):
        try:
            rows = await fetch_all(
                "SELECT * FROM applications WHERE status IN ('PENDING','CLAIMED') "
                "AND claimed_by IS NOT NULL AND claimed_by != '' AND nudged_at IS NULL"
            )
        except Exception as e:
            print(f"[ApplicationsCog] nudge warn fetch: {e}")
            return
        now = datetime.now(timezone.utc)
        for row in rows:
            try:
                ts = _parse_ts(row.get("claimed_at"))
                if not ts or (now - ts).total_seconds() < 600:
                    continue
                guild = await find_guild_for_channel(self.bot, int(row["log_channel_id"])) if row.get("log_channel_id") else None
                if guild is None:
                    continue
                thread = guild.get_thread(int(row["thread_id"])) if row.get("thread_id") else None
                if thread is None:
                    continue
                link = ""
                if row.get("site_id"):
                    link = f"\nhttps://botdiscord-87a.pages.dev/applications/{row['site_id']}"
                await thread.send(
                    f"⏰ <@{row['claimed_by']}> ты взял заявку 10 минут назад, но решения нет.{link}")
                await execute("UPDATE applications SET nudged_at=? WHERE id=?",
                              (now_iso(), row["id"]))
            except Exception as e:
                print(f"[ApplicationsCog] nudge warn: {e}")

    @nudge_loop.before_loop
    async def _before_nudge(self):
        await self.bot.wait_until_ready()

    async def _poll_guild(self, guild: discord.Guild):
        gid = str(guild.id)
        cursor = await get_setting(SET_APPS_POLL_CURSOR_KEY, gid) or "1970-01-01 00:00:00"
        try:
            data = await asyncio.to_thread(
                _api_req, "GET",
                f"/guilds/{gid}/applications-updates?since={urllib.parse.quote(cursor)}")
        except Exception as e:
            print(f"[ApplicationsCog] poll api warn: {e}")
            return
        if not data:
            return
        newest = cursor
        for app in data.get("applications", []) or []:
            try:
                await self._apply_site_app(guild, app)
            except Exception as e:
                print(f"[ApplicationsCog] apply warn: {e}")
            if str(app.get("updated_at") or "") > newest:
                newest = str(app.get("updated_at"))
        for m in data.get("outbox", []) or []:
            try:
                await self._deliver_outbox(guild, m)
            except Exception as e:
                print(f"[ApplicationsCog] outbox warn: {e}")
        if newest != cursor:
            await set_setting(SET_APPS_POLL_CURSOR_KEY, newest, gid)

    @staticmethod
    def _site_to_local(status: str | None) -> str:
        return {"approved": "ACCEPTED", "rejected": "REJECTED"}.get((status or "").lower(), "PENDING")

    async def _apply_site_app(self, guild: discord.Guild, app: dict):
        gid = str(guild.id)
        ext = app.get("external_id")
        sid = app.get("id")
        local = None
        if ext:
            local = await fetch_one("SELECT * FROM applications WHERE id=?", (ext,))
        if not local and sid:
            local = await fetch_one("SELECT * FROM applications WHERE site_id=?", (sid,))
        if not local:
            nid = ext or str(uuid.uuid4())
            st = self._site_to_local(app.get("status"))
            await execute(
                """INSERT OR IGNORE INTO applications
                   (id, discord_user_id, guild_id, created_at, status, site_id,
                    claimed_by, decided_by, decision_reason, thread_id,
                    log_channel_id, log_message_id, answers)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (nid, app.get("discord_id"), gid, app.get("created_at"), st, sid,
                 app.get("claimed_by"), app.get("decided_by"), app.get("admin_notes"),
                 app.get("thread_id"), app.get("log_channel_id") or "",
                 app.get("log_message_id") or "", app.get("answers")),
            )
            local = await fetch_one("SELECT * FROM applications WHERE id=?", (nid,))
            if not local:
                print(f"[ApplicationsCog] mirror failed silently for site #{sid}")
                return
            if local and st == "PENDING":
                await self._post_panel_for_mirror(guild, local)
            return
        if not local.get("site_id") and sid:
            await execute("UPDATE applications SET site_id=? WHERE id=?", (sid, local["id"]))
        if app.get("claimed_by") and not local.get("claimed_by"):
            await execute(
                "UPDATE applications SET claimed_by=?, claimed_at=?, status='CLAIMED' WHERE id=?",
                (app["claimed_by"], now_iso(), local["id"]),
            )
            await self.refresh_message(local["id"])
            await self._thread_note(guild, local["id"], f"📌 Заявку взял с сайта: <@{app['claimed_by']}>")
        st = self._site_to_local(app.get("status"))
        if st in ("ACCEPTED", "REJECTED") and (local.get("status") or "") in ("PENDING", "CLAIMED"):
            await self._apply_site_decision(guild, local, st == "ACCEPTED",
                                            app.get("decided_by"), app.get("admin_notes"))

    async def _post_panel_for_mirror(self, guild: discord.Guild, local: dict):
        app_id = local["id"]
        ch = await get_log_channel(guild)
        if ch is None:
            return
        try:
            answers = json.loads(local.get("answers") or "{}")
        except Exception:
            answers = {}
        questions = await get_questions(str(guild.id))
        labels = {str(q.get("id")): str(q.get("label")) for q in questions}
        embed = discord.Embed(title="📨 Заявка в семью (с сайта)", color=0x9B59B6)
        for qid, val in (answers or {}).items():
            embed.add_field(name=labels.get(str(qid), str(qid))[:256],
                            value=str(val)[:1024] or "—", inline=False)
        embed.add_field(name="Discord", value=f"<@{local['discord_user_id']}>", inline=False)
        embed.set_footer(text=f"{APP_TAG} app_id={app_id}")
        pings = await recruiter_pings(str(guild.id))
        panel_msg = await ch.send(content=pings, embed=embed, view=ApplicationView(self, app_id))
        thread = await panel_msg.create_thread(
            name=f"Заявка {app_id[:8]}", auto_archive_duration=1440,
            reason=f"Чат по заявке {app_id} (с сайта)",
        )
        await execute(
            "UPDATE applications SET log_channel_id=?, log_message_id=?, thread_id=? WHERE id=?",
            (str(ch.id), str(panel_msg.id), str(thread.id), app_id),
        )
        try:
            from services.api_sync import queue_application_sync
            queue_application_sync(str(guild.id), app_id, str(local["discord_user_id"]),
                                   local.get("status") or "PENDING",
                                   log_channel_id=str(ch.id), log_message_id=str(panel_msg.id),
                                   thread_id=str(thread.id))
        except Exception as e:
            print(f"[api_sync] warn: {e}")
        await self.refresh_message(app_id)

    async def _thread_note(self, guild: discord.Guild, app_id: str, note: str):
        row = await fetch_one("SELECT thread_id FROM applications WHERE id=?", (app_id,))
        if not row or not row.get("thread_id"):
            return
        try:
            thread = guild.get_thread(int(row["thread_id"]))
            if thread is None:
                return
            await thread.send(note[:1800])
        except Exception as e:
            print(f"[ApplicationsCog] thread note warn: {e}")

    async def _apply_site_decision(self, guild: discord.Guild, local: dict,
                                   accepted: bool, decider_id: str | None, reason: str | None):
        app_id = local["id"]
        member = await fetch_member_safe(guild, int(local["discord_user_id"]))
        new_status = "ACCEPTED" if accepted else "REJECTED"
        await execute(
            "UPDATE applications SET status=?, decided_by=?, decided_at=?, decision_reason=? WHERE id=?",
            (new_status, str(decider_id or ""), now_iso(), reason, app_id),
        )
        if member is not None:
            temp_role = await get_temp_role(guild)
            if temp_role and temp_role in member.roles:
                try:
                    await member.remove_roles(temp_role, reason="Заявка закрыта (сайт)")
                except Exception:
                    pass
                await execute("UPDATE applications SET temp_role_given=0 WHERE id=?", (app_id,))
            if accepted:
                role_ids = parse_id_list(await get_setting(SET_ACCEPT_ROLES_KEY, str(guild.id))
                                         or await get_setting(SET_ACCEPT_ROLES_KEY))
                roles = [guild.get_role(rid) for rid in role_ids]
                roles = [r for r in roles if r is not None]
                if roles:
                    try:
                        await member.add_roles(*roles, reason=f"Заявка {app_id} принята (сайт)")
                    except Exception as e:
                        print(f"[ApplicationsCog] site accept roles warn: {e}")
            else:
                remove_ids = parse_id_list(await get_setting(SET_REJECT_ROLES_KEY, str(guild.id))
                                           or await get_setting(SET_REJECT_ROLES_KEY))
                roles = [guild.get_role(rid) for rid in remove_ids]
                roles = [r for r in roles if r is not None and r in member.roles]
                if roles:
                    try:
                        await member.remove_roles(*roles, reason=f"Заявка {app_id} отклонена (сайт)")
                    except Exception as e:
                        print(f"[ApplicationsCog] site reject roles warn: {e}")
        await self.refresh_message(app_id, remove_buttons=True,
                                   color=(discord.Color.green() if accepted else discord.Color.red()))
        try:
            if member is not None:
                if accepted:
                    await member.send(f"✅ Твоя заявка ({app_id[:8]}) принята!")
                else:
                    await member.send(f"❌ Твоя заявка ({app_id[:8]}) отклонена. Причина: {reason or '—'}")
        except Exception:
            pass
        status_text = "принята" if accepted else "отклонена"
        await self.close_thread_for_app(guild, app_id, note=f"🔒 Заявка {status_text} (сайт). Thread закрыт.")
        try:
            from services.api_sync import queue_application_sync
            queue_application_sync(str(guild.id), app_id, str(local["discord_user_id"]), new_status, reason,
                                   decided_by=str(decider_id or ""))
        except Exception as e:
            print(f"[api_sync] warn: {e}")

    async def _deliver_outbox(self, guild: discord.Guild, m: dict):
        site_id = m.get("application_id")
        local = await fetch_one("SELECT * FROM applications WHERE site_id=?", (site_id,))
        if not local or not local.get("thread_id"):
            return
        thread = guild.get_thread(int(local["thread_id"]))
        if thread is None:
            return
        author_id = str(m.get("author_discord_id") or "")
        try:
            member = guild.get_member(int(author_id)) or await guild.fetch_member(int(author_id))
            name = member.display_name
        except Exception:
            name = author_id
        try:
            await thread.send(f"💬 С сайта от {name}:\n{str(m.get('content') or '')[:1800]}")
        except Exception as e:
            print(f"[ApplicationsCog] outbox send warn: {e}")
            return
        try:
            await asyncio.to_thread(
                _api_req, "POST", f"/guilds/{guild.id}/applications/{site_id}/delivered",
                {"message_ids": [m.get("id")]})
        except Exception as e:
            print(f"[ApplicationsCog] delivered mark warn: {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if self.bot.user and message.author.id == self.bot.user.id:
            return

        if message.guild is None and isinstance(message.channel, discord.DMChannel):
            row = await fetch_one(
                "SELECT * FROM applications "
                "WHERE discord_user_id=? AND status IN ('PENDING','CLAIMED') "
                "ORDER BY created_at DESC LIMIT 1",
                (str(message.author.id),),
            )
            if not row:
                return

            thread_id = row.get("thread_id")
            if not thread_id:
                return

            guild = None
            for g in list(self.bot.guilds):
                t = g.get_thread(int(thread_id))
                if t is not None:
                    guild = g
                    thread = t
                    break
            else:
                thread = None

            if thread is None:
                try:
                    guild = await find_guild_for_channel(self.bot, int(row["log_channel_id"]))
                    if guild is None:
                        return
                    ch = guild.get_channel(int(row["log_channel_id"])) or await guild.fetch_channel(int(row["log_channel_id"]))
                    thread = await ch.fetch_channel(int(thread_id))
                except:
                    thread = None

            if thread is None or guild is None:
                return

            content = message.content.strip()
            if content:
                await thread.send(f"📩 От кандидата <@{message.author.id}>:\n{content[:1800]}")
                try:
                    from services.api_sync import queue_app_message
                    queue_app_message(str(guild.id), row["id"], str(message.author.id), content[:1800])
                except Exception as e:
                    print(f"[api_sync] warn: {e}")

            if message.attachments:
                links = "\n".join(a.url for a in message.attachments)[:1800]
                await thread.send(f"📎 Вложения от кандидата:\n{links}")

            return

        if message.guild is None:
            return

        if isinstance(message.channel, discord.Thread):
            row = await fetch_one(
                "SELECT * FROM applications WHERE thread_id=? LIMIT 1",
                (str(message.channel.id),),
            )
            if not row:
                return

            author = message.author
            if not isinstance(author, discord.Member):
                return

            claimed_by = row.get("claimed_by")
            # Писать может только взявший + админы (Discord-админ или панельный admin/owner)
            prole = await panel_role_of(str(message.guild.id), str(author.id))
            allowed = (
                is_admin(author)
                or prole in ("admin", "owner")
                or (claimed_by and int(claimed_by) == author.id)
            )
            if not allowed:
                try:
                    await message.delete()
                except Exception:
                    pass
                return

            cand_id = int(row["discord_user_id"])
            cand = await fetch_member_safe(message.guild, cand_id)

            if cand is None:
                await message.channel.send("⚠️ Кандидат покинул сервер, сообщение не доставлено.")
                return

            text = message.content.strip()
            if text:
                ok = await safe_dm(cand, f"💬 Сообщение по твоей заявке от {author.display_name}:\n{text[:1800]}")
                if not ok:
                    await message.channel.send("⚠️ Не смог отправить кандидату ЛС (закрыты DM).")
                try:
                    from services.api_sync import queue_app_message
                    queue_app_message(str(message.guild.id), row["id"], str(author.id), text[:1800])
                except Exception as e:
                    print(f"[api_sync] warn: {e}")

            if message.attachments:
                links = "\n".join(a.url for a in message.attachments)[:1800]
                ok = await safe_dm(cand, f"📎 Вложения от рекрутера:\n{links}")
                if not ok:
                    await message.channel.send("⚠️ Не смог отправить кандидату ЛС (закрыты DM).")

            return

        if message.channel.id == LOG_CHANNEL_ID and message.webhook_id is not None:
            if not message.embeds:
                return

            emb, app_id, cand_id = find_app_embed(message.embeds)
            if not emb or not app_id or not cand_id:
                return

            ping_role_id = parse_single_id(await get_setting(SET_APPS_PING_ROLE_KEY))
            content = f"<@&{ping_role_id}>" if ping_role_id else None

            panel_msg = await message.channel.send(
                content=content,
                embed=emb,
                view=ApplicationView(self, app_id),
                allowed_mentions=discord.AllowedMentions(roles=True) if ping_role_id else discord.AllowedMentions.none(),
            )

            await execute(
                "INSERT OR REPLACE INTO applications (id, discord_user_id, created_at, status, log_channel_id, log_message_id) "
                "VALUES (?, ?, ?, 'PENDING', ?, ?)",
                (app_id, str(cand_id), now_iso(), str(message.channel.id), str(panel_msg.id)),
            )
            try:
                from services.api_sync import queue_application_sync
                queue_application_sync(str(message.guild.id), app_id, str(cand_id), "PENDING",
                                       log_channel_id=str(message.channel.id),
                                       log_message_id=str(panel_msg.id))
            except Exception as e:
                print(f"[api_sync] warn: {e}")

            await self.refresh_message(app_id)

            try:
                await message.delete()
            except:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(ApplicationsCog(bot))
