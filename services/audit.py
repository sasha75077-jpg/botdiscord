# services/audit.py
import discord
from database import get_setting

async def send_audit_log(client: discord.Client, embed: discord.Embed, key: str) -> bool:
    raw = await get_setting(key)
    if not raw:
        return False
    try:
        channel_id = int(raw)
    except (TypeError, ValueError):
        return False

    try:
        ch = client.get_channel(channel_id) or await client.fetch_channel(channel_id)
        await ch.send(embed=embed)
        return True
    except (discord.Forbidden, discord.NotFound, discord.HTTPException):
        return False

async def audit_contracts(client, embed, guild_id: str | None = None):
    # Сначала per-guild канал (настраивается на сайте), потом глобальный
    if guild_id:
        try:
            raw = await get_setting("contracts_audit_channel_id", str(guild_id))
            if raw and str(raw).strip().isdigit():
                ch = client.get_channel(int(raw)) or await client.fetch_channel(int(raw))
                await ch.send(embed=embed)
                return True
        except Exception:
            pass
    return await send_audit_log(client, embed, "log_contracts")

async def audit_bonus(client, embed):       return await send_audit_log(client, embed, "log_bonus")
async def audit_promotions(client, embed):  return await send_audit_log(client, embed, "log_promo")

async def audit_bonus_log(client, embed, guild_id: str | None = None):
    if guild_id:
        try:
            raw = await get_setting("bonus_audit_channel_id", str(guild_id))
            if not raw:
                raw = await get_setting("bonus_log_channel_id", str(guild_id))
            if raw and str(raw).strip().isdigit():
                ch = client.get_channel(int(raw)) or await client.fetch_channel(int(raw))
                await ch.send(embed=embed)
                return True
        except Exception:
            pass
    return await send_audit_log(client, embed, "log_bonus_audit")
