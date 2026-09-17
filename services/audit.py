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

async def audit_contracts(client, embed):   return await send_audit_log(client, embed, "log_contracts")
async def audit_bonus(client, embed):       return await send_audit_log(client, embed, "log_bonus")
async def audit_promotions(client, embed):  return await send_audit_log(client, embed, "log_promo")

async def audit_bonus_log(client, embed):
    return await send_audit_log(client, embed, "log_bonus_audit")