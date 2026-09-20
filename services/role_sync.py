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
import urllib.request

import discord

from database import execute, fetch_all, fetch_one, get_setting

API_URL = os.getenv("PANEL_API_URL", "https://melancholia-api.sasha75077.workers.dev").rstrip("/")
SYNC_SECRET = os.getenv("PANEL_SYNC_SECRET", "")

ADMIN_KEY = "panel_admin_role_ids"
RECRUIT_KEY = "panel_recruiter_role_ids"
SYNC_MARK = "discord-sync"


def _parse_ids(s):
    return [x.strip() for x in (s or "").split(",") if x.strip().isdigit()]


def _api_get(path):
    req = urllib.request.Request(API_URL + path, method="GET")
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def _api_post(path, payload):
    if not SYNC_SECRET:
        return
    req = urllib.request.Request(
        API_URL + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {SYNC_SECRET}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        r.read()


def _api_delete(path):
    if not SYNC_SECRET:
        return
    req = urllib.request.Request(
        API_URL + path,
        headers={"Authorization": f"Bearer {SYNC_SECRET}"},
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
    """Полная сверка сервера."""
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
