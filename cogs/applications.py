import re
from datetime import datetime, timezone

import discord
from discord.ext import commands

from database import execute, fetch_one, get_setting

GUILD_ID = 880440495233454080
LOG_CHANNEL_ID = 1386771246733066433

RECRUIT_ROLE_ID = 1405605410018295989
TEMP_CALL_ROLE_ID = 1307538910964093020

APP_TAG = "FAMU_APP"

SET_ACCEPT_ROLES_KEY = "app_accept_roles"
SET_REJECT_ROLES_KEY = "app_reject_remove_roles"
SET_APPS_PING_ROLE_KEY = "applications_ping_role_id"


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


class ApplicationView(discord.ui.View):
    def __init__(self, cog: "ApplicationsCog", app_id: str):
        super().__init__(timeout=None)
        self.cog = cog
        self.app_id = app_id

    def allowed(self, member: discord.Member) -> bool:
        return is_admin(member) or any(r.id == RECRUIT_ROLE_ID for r in member.roles)

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
        if not self.allowed(interaction.user):
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
        if not self.allowed(interaction.user):
            return await interaction.response.send_message("❌ Нет доступа.", ephemeral=True)

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
        if not self.allowed(interaction.user):
            return await interaction.response.send_message("❌ Нет доступа.", ephemeral=True)

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

        if not self._did_rescan:
            self._did_rescan = True
            try:
                await self.rescan_last_apps(limit=20, debug=False)
            except Exception as e:
                print("[ApplicationsCog] rescan failed:", repr(e))

        print("[ApplicationsCog] ready")

    async def rescan_last_apps(self, limit: int = 20, debug: bool = False):
        guild = self.bot.get_guild(GUILD_ID) or await self.bot.fetch_guild(GUILD_ID)
        ch = guild.get_channel(LOG_CHANNEL_ID) or await guild.fetch_channel(LOG_CHANNEL_ID)

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
            await msg.edit(embed=embed, view=ApplicationView(self, app_id))

    async def claim(self, app_id: str, interaction: discord.Interaction):
        row = await fetch_one("SELECT * FROM applications WHERE id=?", (app_id,))
        if not row:
            return False, "❌ Не нашёл заявку в БД."
        if row["status"] in ("ACCEPTED", "REJECTED"):
            return False, "❌ Заявка уже закрыта."

        if (
            row["status"] == "CLAIMED"
            and row.get("claimed_by")
            and int(row["claimed_by"]) != interaction.user.id
            and not is_admin(interaction.user)
        ):
            cb = row.get("claimed_by")
            return False, f"❌ Эту заявку уже рассматривает <@{cb}>."

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
            "UPDATE applications SET status='CLAIMED', claimed_by=?, claimed_at=? WHERE id=?",
            (str(recruiter.id), now_iso(), app_id),
        )
        try:
            from services.api_sync import queue_application_sync
            queue_application_sync(str(guild.id), app_id, str(cand_id), "CLAIMED",
                                   claimed_by=str(recruiter.id))
        except Exception as e:
            print(f"[api_sync] warn: {e}")

        temp_role = guild.get_role(TEMP_CALL_ROLE_ID)
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

        temp_role = guild.get_role(TEMP_CALL_ROLE_ID)
        if temp_role and temp_role in member.roles:
            await member.remove_roles(temp_role, reason="Заявка закрыта")
            await execute("UPDATE applications SET temp_role_given=0 WHERE id=?", (app_id,))

        if accepted:
            role_ids = parse_id_list(await get_setting(SET_ACCEPT_ROLES_KEY))
            roles = [guild.get_role(rid) for rid in role_ids]
            roles = [r for r in roles if r is not None]
            if roles:
                await member.add_roles(*roles, reason=f"Заявка {app_id} принята")
        else:
            remove_ids = parse_id_list(await get_setting(SET_REJECT_ROLES_KEY))
            roles = [guild.get_role(rid) for rid in remove_ids]
            roles = [r for r in roles if r is not None and r in member.roles]
            if roles:
                await member.remove_roles(*roles, reason=f"Заявка {app_id} отклонена")

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

            guild = self.bot.get_guild(GUILD_ID) or await self.bot.fetch_guild(GUILD_ID)
            thread = guild.get_thread(int(thread_id))

            if thread is None:
                try:
                    ch = guild.get_channel(int(row["log_channel_id"])) or await guild.fetch_channel(int(row["log_channel_id"]))
                    thread = await ch.fetch_channel(int(thread_id))
                except:
                    thread = None

            if thread is None:
                return

            content = message.content.strip()
            if content:
                await thread.send(f"📩 От кандидата <@{message.author.id}>:\n{content[:1800]}")

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
            allowed = (
                is_admin(author)
                or any(r.id == RECRUIT_ROLE_ID for r in author.roles)
                or (claimed_by and int(claimed_by) == author.id)
            )
            if not allowed:
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
