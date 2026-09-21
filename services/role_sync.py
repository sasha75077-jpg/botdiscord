"""Сверка Discord-ролей <-> панельных прав (admin/recruiter).

Источники истины:
- Привязки Discord-роль -> панельная роль: guild_settings
  (panel_admin_role_ids, panel_recruiter_role_ids, через запятую).
  Читаются из API панели, при недоступности - локально.
- permissions.granted_by = 'discord-sync' - автоназначенные (снимаются
  при потере Discord-роли). Остальные (ручные) - не трогаем.
- Ручные admin/recruiter без Discord-роли бот пытается выдать сам
  (по первой привязанной роли); нет прав - пишет в bot_logs + audit.
"""
import asyncio
import json
import os
import urllib.parse
import urllib.request

import discord

from database import execute, fetch_all, fetch_one, get_setting, set_setting

API_URL = os.getenv("PANEL_API_URL", "https://melancholia-api.sasha75077.workers.dev").rstrip("/")
SYNC_SECRET = os.getenv("PANEL_SYNC_SECRET", "")
BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

ADMIN_KEY = "panel_admin_role_ids"
RECRUIT_KEY = "panel_recruiter_role_ids"
SYNC_MARK = "discord-sync"


def _parse_ids(s):
    return [x.strip() for x in (s or "").split(",") if x.strip().isdigit()]


def _api_get(path):
    req = urllib.request.Request(API_URL + path, method="GET",
                                 headers={"User-Agent": BROWSER_UA})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def _api_post(path, payload):
    if not SYNC_SECRET:
        return
    req = urllib.request.Request(
        API_URL + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {SYNC_SECRET}",
                 "User-Agent": BROWSER_UA},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        r.read()


def _api_delete(path):
    if not SYNC_SECRET:
        return
    req = urllib.request.Request(
        API_URL + path,
        headers={"Authorization": f"Bearer {SYNC_SECRET}", "User-Agent": BROWSER_UA},
        method="DELETE",
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        r.read()


async def bot_log(bot, guild_id, message, level="error", source="role-sync"):
    """Лог овнеру: в D1 (видно на сайте) + в audit-канал Discord."""
    try:
        await asyncio.to_thread(_api_post, f"/guilds/{guild_id}/bot-logs",
                                {"level": level, "source": source, "message": message})
    except Exception as e:
        print(f"[role-sync] warn log api: {e}")
    try:
        guild = bot.get_guild(int(guild_id))
        if guild is None:
            return
        ch_id = await get_setting("audit_log_channel_id", guild_id)
        if not ch_id:
            return
        channel = guild.get_channel(int(ch_id))
        if channel is None:
            return
        color = 0xE74C3C if level == "error" else 0x2ECC71
        embed = discord.Embed(title="🔐 Роли панели", description=message[:4000], color=color)
        await channel.send(embed=embed)
    except Exception as e:
        print(f"[role-sync] warn log audit: {e}")


async def pull_remote_state(guild_id):
    """Подтянуть настройки/модули с сайта в локальную БД."""
    applied = 0
    try:
        data = await asyncio.to_thread(_api_get, f"/guilds/{guild_id}/settings")
    except Exception as e:
        print(f"[role-sync] warn pull settings: {e}")
        return 0
    remote = (data or {}).get("settings", {}) or {}
    remote_updated = (data or {}).get("updated_at", {}) or {}
    if remote:
        local_rows = await fetch_all(
            "SELECT setting_key, setting_value, updated_at FROM guild_settings WHERE guild_id = ?",
            (guild_id,),
        )
        local = {r["setting_key"]: r for r in local_rows}
        for key, value in remote.items():
            if value is None:
                continue
            cur = local.get(key)
            r_updated = str(remote_updated.get(key) or "")
            l_updated = str((cur or {}).get("updated_at") or "")
            if cur is None or (r_updated and r_updated >= l_updated):
                if cur is None or str(cur.get("setting_value") or "") != str(value):
                    await execute(
                        """INSERT INTO guild_settings (guild_id, setting_key, setting_value, updated_at)
                           VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                           ON CONFLICT(guild_id, setting_key) DO UPDATE SET
                               setting_value = excluded.setting_value,
                               updated_at = CURRENT_TIMESTAMP""",
                        (guild_id, key, str(value)),
                    )
                    applied += 1
    try:
        mdata = await asyncio.to_thread(_api_get, f"/guilds/{guild_id}/modules")
    except Exception as e:
        print(f"[role-sync] warn pull modules: {e}")
        return applied
    for m in (mdata or {}).get("modules", []) or []:
        try:
            await execute(
                """INSERT INTO guild_modules (guild_id, module_name, is_enabled)
                   VALUES (?, ?, ?)
                   ON CONFLICT(guild_id, module_name) DO UPDATE SET is_enabled = ?""",
                (guild_id, m["module_name"], 1 if m["is_enabled"] else 0,
                 1 if m["is_enabled"] else 0),
            )
        except Exception as e:
            print(f"[role-sync] warn pull module {m}: {e}")
    return applied


async def get_mapping(guild_id):
    """{admin_ids: [...], recruit_ids: [...]} - API приоритет, локально fallback."""
    remote = {}
    try:
        data = await asyncio.to_thread(_api_get, f"/guilds/{guild_id}/settings")
        remote = (data or {}).get("settings", {}) or {}
    except Exception as e:
        print(f"[role-sync] warn settings api: {e}")
    if ADMIN_KEY in remote or RECRUIT_KEY in remote:
        return {
            "admin_ids": _parse_ids(remote.get(ADMIN_KEY, "")),
            "recruit_ids": _parse_ids(remote.get(RECRUIT_KEY, "")),
        }
    rows = await fetch_all(
        "SELECT setting_key, setting_value FROM guild_settings WHERE guild_id = ? AND setting_key IN (?, ?)",
        (guild_id, ADMIN_KEY, RECRUIT_KEY),
    )
    local = {r["setting_key"]: r["setting_value"] for r in rows}
    return {
        "admin_ids": _parse_ids(local.get(ADMIN_KEY, "")),
        "recruit_ids": _parse_ids(local.get(RECRUIT_KEY, "")),
    }


def _desired(role_ids, mapping):
    if role_ids & set(mapping["admin_ids"]):
        return "admin"
    if role_ids & set(mapping["recruit_ids"]):
        return "recruiter"
    return None


async def _api_grant(guild_id, discord_id, role):
    try:
        await asyncio.to_thread(
            _api_post, f"/guilds/{guild_id}/permissions",
            {"discord_id": discord_id, "role": role, "granted_by": SYNC_MARK},
        )
    except Exception as e:
        print(f"[role-sync] warn api grant: {e}")


async def _api_revoke_synced(guild_id, discord_id):
    try:
        await asyncio.to_thread(
            _api_delete, f"/guilds/{guild_id}/permissions/{discord_id}?only_synced=1"
        )
    except Exception as e:
        print(f"[role-sync] warn api revoke: {e}")


async def reconcile_member(bot, guild, member):
    """Сверить одного участника. Возвращает True если что-то менялось."""
    if member.bot:
        return False
    guild_id = str(guild.id)
    discord_id = str(member.id)
    mapping = await get_mapping(guild_id)
    if not mapping["admin_ids"] and not mapping["recruit_ids"]:
        return False  # привязки не настроены

    role_ids = {str(r.id) for r in member.roles}
    desired = _desired(role_ids, mapping)
    row = await fetch_one(
        "SELECT role, granted_by FROM permissions WHERE guild_id = ? AND discord_id = ?",
        (guild_id, discord_id),
    )
    changed = False

    if desired:
        if not row or row["role"] != desired or row["granted_by"] != SYNC_MARK:
            await execute(
                """INSERT INTO permissions (guild_id, discord_id, role, granted_by)
                   VALUES (?, ?, ?, 'discord-sync')
                   ON CONFLICT(guild_id, discord_id) DO UPDATE SET role = ?, granted_by = 'discord-sync'""",
                (guild_id, discord_id, desired, desired),
            )
            await _api_grant(guild_id, discord_id, desired)
            changed = True
    else:
        if row and row["granted_by"] == SYNC_MARK:
            await execute(
                "DELETE FROM permissions WHERE guild_id = ? AND discord_id = ? AND granted_by = 'discord-sync'",
                (guild_id, discord_id),
            )
            await _api_revoke_synced(guild_id, discord_id)
            changed = True
            return changed

    # Ручные admin/recruiter: Discord-роль должна быть, выдаем сами
    current = await fetch_one(
        "SELECT role, granted_by FROM permissions WHERE guild_id = ? AND discord_id = ?",
        (guild_id, discord_id),
    )
    if current and current["role"] in ("admin", "recruiter") and (current["granted_by"] or "") != SYNC_MARK:
        want_ids = mapping["admin_ids"] if current["role"] == "admin" else mapping["recruit_ids"]
        if not want_ids:
            await bot_log(bot, guild_id,
                          f"У {member} ({discord_id}) панельная роль {current['role']}, "
                          f"но привязка Discord-роли не настроена ({ADMIN_KEY if current['role'] == 'admin' else RECRUIT_KEY}).")
        elif not (role_ids & set(want_ids)):
            role_obj = guild.get_role(int(want_ids[0]))
            if role_obj is None:
                await bot_log(bot, guild_id, f"Привязанная роль {want_ids[0]} не найдена на сервере.")
            else:
                try:
                    await member.add_roles(role_obj, reason=f"Панельная роль {current['role']}")
                    changed = True
                except discord.Forbidden:
                    await bot_log(bot, guild_id,
                                  f"Нет прав выдать Discord-роль {role_obj.name} пользователю {member} ({discord_id}). "
 f"Проверь иерархию ролей и право Manage Roles у бота.")
                except Exception as e:
                    await bot_log(bot, guild_id, f"Не смог выдать роль {member} ({discord_id}): {e}")
    return changed


async def reconcile_guild(bot, guild):
    mapping = await get_mapping(str(guild.id))
    if not mapping["admin_ids"] and not mapping["recruit_ids"]:
        return 0
    try:
        members = list(guild.members) or [m async for m in guild.fetch_members(limit=None)]
    except Exception as e:
        print(f"[role-sync] warn members {guild.id}: {e}")
        return 0
    changed = 0
    for member in members:
        try:
            if await reconcile_member(bot, guild, member):
                changed += 1
        except Exception as e:
            print(f"[role-sync] warn {member.id}: {e}")
    if changed:
        print(f"[role-sync] {guild.name}: {changed} изменений")
    return changed


SITE_TO_LOCAL_STATUS = {"pending": "PENDING", "approved": "APPROVED", "rejected": "REJECTED"}


async def poll_site_bonus():
    """Забрать премии с сайта в локальную БД (черновики)."""
    if not SYNC_SECRET:
        return
    try:
        guilds = await fetch_all("SELECT guild_id FROM guilds WHERE is_active = 1")
    except Exception as e:
        print(f"[bonus-poll] warn guilds: {e}")
        return
    for g in guilds:
        gid = str(g["guild_id"])
        try:
            await _poll_guild_bonus(gid)
        except Exception as e:
            print(f"[bonus-poll] warn {gid}: {e}")


async def _poll_guild_bonus(guild_id: str):
    cursor = await get_setting("bonus_poll_cursor", guild_id) or "1970-01-01 00:00:00"
    try:
        data = await asyncio.to_thread(
            _api_get, f"/guilds/{guild_id}/bonus?status=pending&since={urllib.parse.quote(cursor)}")
    except Exception as e:
        print(f"[bonus-poll] warn api: {e}")
        return
    rows = data if isinstance(data, list) else []
    newest = cursor
    for r in rows:
        try:
            ts = str(r.get("updated_at") or r.get("created_at") or "")
            if ts > newest:
                newest = ts
            if not r.get("id"):
                continue
            exists = await fetch_one("SELECT report_id FROM bonus_reports WHERE site_id = ?", (r["id"],))
            if exists:
                continue
            week = str(r.get("reason") or "")
            ws, we = (week.split("..") + ["", ""])[:2]
            await execute(
                """INSERT INTO bonus_reports
                   (guild_id, discord_id, week_start, week_end, total_amount,
                    contracts_json, submitted_at, status, site_id)
                   VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 'NEW', ?)""",
                (guild_id, str(r.get("recipient_discord_id") or r.get("discord_id")),
                 ws, we, float(r.get("amount") or 0),
                 r.get("contracts_json") or "[]", r["id"]),
            )
        except Exception as e:
            print(f"[bonus-poll] warn row: {e}")
    if newest != cursor:
        await set_setting("bonus_poll_cursor", newest, guild_id)


async def push_users(guild_id: str):
    """Залить юзеров сервера на сайт (static и членство)."""
    if not SYNC_SECRET:
        return 0
    try:
        rows = await fetch_all(
            "SELECT discord_id, static FROM users WHERE guild_id = ?", (guild_id,))
    except Exception as e:
        print(f"[users-push] warn fetch: {e}")
        return 0
    if not rows:
        return 0
    try:
        await asyncio.to_thread(
            _api_post, f"/guilds/{guild_id}/users/sync",
            {"users": [{"discord_id": r["discord_id"], "static": r.get("static")} for r in rows]})
        return len(rows)
    except Exception as e:
        print(f"[users-push] warn api: {e}")
        return 0


def _api_post(path, payload):
    import urllib.request as _u
    import json as _j
    import os as _o
    key = _o.getenv("PANEL_SYNC_SECRET", "")
    if not key:
        return
    req = _u.Request(
        API_URL + path,
        data=_j.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}",
                 "User-Agent": BROWSER_UA},
        method="POST",
    )
    with _u.urlopen(req, timeout=30) as r:
        r.read()


async def nudge_site_contracts(bot):
    if bot is None:
        return
    try:
        rows = await fetch_all(
            "SELECT * FROM contracts WHERE confirm_status = 'PENDING' "
            "AND claimed_by IS NOT NULL AND claimed_by != '' AND nudged_at IS NULL "
            "AND site_id IS NOT NULL"
        )
    except Exception as e:
        print(f"[contracts-nudge] warn fetch: {e}")
        return
    from datetime import datetime as _dt, timezone as _tz
    now = _dt.now(_tz.utc)
    for r in rows:
        try:
            ts = _parse_ts(r.get("claimed_at"))
            if not ts or (now - ts).total_seconds() < 600:
                continue
            guild = bot.get_guild(int(r["guild_id"]))
            if guild is None:
                continue
            ch_id = None
            try:
                det = r.get("details")
                if isinstance(det, str):
                    det = json.loads(det)
                ch_id = ((det or {}).get("upload") or {}).get("channel_id")
            except Exception:
                ch_id = None
            if not ch_id:
                cfg = await fetch_all(
                    "SELECT setting_value FROM guild_settings WHERE guild_id = ? AND setting_key IN ('contracts_upload_channel_id', 'contracts_log_channel_id')",
                    (str(r["guild_id"]),),
                )
                for row in cfg:
                    if (row["setting_value"] or "").strip().isdigit():
                        ch_id = row["setting_value"].strip()
                        break
            if not ch_id:
                continue
            channel = guild.get_channel(int(ch_id))
            if channel is None:
                try:
                    channel = await guild.fetch_channel(int(ch_id))
                except Exception:
                    continue
            link = f"https://botdiscord-87a.pages.dev/contracts/{r['site_id']}"
            await channel.send(
                f"⏰ <@{r['claimed_by']}> ты взял контракт #{r['site_id']} 10 минут назад, но решения нет.\n{link}")
            await execute("UPDATE contracts SET nudged_at = CURRENT_TIMESTAMP WHERE id = ?",
                          (r["id"],))
        except Exception as e:
            print(f"[contracts-nudge] warn: {e}")


def _parse_ts(s):
    if not s:
        return None
    from datetime import datetime as _dt, timezone as _tz
    t = str(s).strip().replace('Z', '+00:00')
    try:
        dt = _dt.fromisoformat(t)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_tz.utc)
    return dt


async def poll_site_contracts(bot=None):
    """Забрать контракты с сайта в локальную БД (новые + решения)."""
    if not SYNC_SECRET:
        return
    try:
        guilds = await fetch_all("SELECT guild_id FROM guilds WHERE is_active = 1")
    except Exception as e:
        print(f"[contracts-poll] warn guilds: {e}")
        return
    for g in guilds:
        gid = str(g["guild_id"])
        try:
            await _poll_guild_contracts(bot, gid)
        except Exception as e:
            print(f"[contracts-poll] warn {gid}: {e}")


async def _poll_guild_contracts(bot, guild_id: str):
    cursor = await get_setting("contracts_poll_cursor", guild_id) or "1970-01-01 00:00:00"
    try:
        data = await asyncio.to_thread(
            _api_get, f"/guilds/{guild_id}/contracts/?limit=500&since={urllib.parse.quote(cursor)}")
    except Exception as e:
        print(f"[contracts-poll] warn api: {e}")
        return
    rows = data if isinstance(data, list) else []
    newest = cursor
    for r in rows:
        try:
            ts = str(r.get("updated_at") or r.get("created_at") or "")
            if ts > newest:
                newest = ts
            await _mirror_site_contract(bot, guild_id, r)
        except Exception as e:
            print(f"[contracts-poll] warn row: {e}")
    if newest != cursor:
        await set_setting("contracts_poll_cursor", newest, guild_id)


async def _mirror_site_contract(bot, guild_id: str, r: dict):
    site_id = r.get("id")
    if not site_id:
        return
    local = await fetch_one("SELECT * FROM contracts WHERE site_id = ?", (site_id,))
    want = SITE_TO_LOCAL_STATUS.get(str(r.get("status") or "pending"), "PENDING")
    if not local:
        if str(r.get("status") or "pending") != "pending":
            return  # старые решения без локальной строки не трогаем
        details = r.get("details")
        await execute(
            """INSERT INTO contracts
               (guild_id, ts, discord_id, contract_type, price, details, confirm_status, source_status, site_id, claimed_by, claimed_at)
               VALUES (?, ?, ?, ?, ?, ?, 'PENDING', 'SITE', ?, ?, ?)""",
            (guild_id, r.get("created_at"), str(r.get("discord_id")),
             str(r.get("contract_type")),
             float(r.get("price") or 0),
             json.dumps(details, ensure_ascii=False) if details else None,
             site_id, r.get("claimed_by"), r.get("claimed_at")),
        )
        try:
            await execute(
                "INSERT OR IGNORE INTO users (discord_id, guild_id) VALUES (?, ?)",
                (str(r.get("discord_id")), guild_id),
            )
        except Exception:
            pass
        await _post_contract_log(bot, guild_id, r)
        return
    updates = []
    if (local.get("confirm_status") or "PENDING") == "PENDING" and want != "PENDING":
        updates.append(("confirm_status", want))
    if (r.get("claimed_by") or None) != (local.get("claimed_by") or None):
        await execute(
            "UPDATE contracts SET claimed_by = ?, claimed_at = ?, nudged_at = NULL WHERE id = ?",
            (r.get("claimed_by"), r.get("claimed_at"), local["id"]),
        )
    if updates:
        await execute(
            "UPDATE contracts SET confirm_status = ? WHERE id = ?",
            (want, local["id"]),
        )
        await _reply_contract_decision(bot, guild_id, r, want)


async def _reply_contract_decision(bot, guild_id: str, r: dict, decision: str):
    """Решение по контракту с сайта - ответом в то же сообщение подачи."""
    if bot is None:
        return
    try:
        details = r.get("details")
        if isinstance(details, str):
            details = json.loads(details)
        upload = (details or {}).get("upload") or {}
        ch_id, msg_id = upload.get("channel_id"), upload.get("message_id")
        if not ch_id or not msg_id:
            return
        guild = bot.get_guild(int(guild_id))
        if guild is None:
            return
        channel = guild.get_channel(int(ch_id))
        if channel is None:
            try:
                channel = await guild.fetch_channel(int(ch_id))
            except Exception:
                return
        try:
            msg = await channel.fetch_message(int(msg_id))
        except Exception:
            return
        mark = "✅ Принят" if decision == "APPROVED" else "❌ Отклонен"
        await msg.reply(f"{mark} (решение с сайта)")
    except Exception as e:
        print(f"[contracts-log] warn: {e}")
