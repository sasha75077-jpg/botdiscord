import discord
from database import fetch_one

MEL_ROLE_ID = 1316909791389679719

async def build_public_panel_embed(guild: discord.Guild) -> discord.Embed:
    role = guild.get_role(MEL_ROLE_ID)
    members = list(role.members) if role else []

    total = len(members)

    online_statuses = {discord.Status.online, discord.Status.idle, discord.Status.dnd}
    online = sum(1 for m in members if m.status in online_statuses)

    row = await fetch_one(
        "SELECT COUNT(*) AS cnt FROM contracts WHERE confirm_status='PENDING' AND (? IS NULL OR guild_id = ?)",
        (str(guild.id), str(guild.id)))
    pending = int(row["cnt"] or 0)

    embed = discord.Embed(
        title="Панель игрока",
        description="Нажми кнопку ниже — профиль откроется только тебе.",
        color=0x3498DB
    )
    embed.add_field(name="Меланхолики (онлайн)", value=str(online), inline=True)
    embed.add_field(name="Меланхолики (всего)", value=str(total), inline=True)
    embed.add_field(name="Ожидание проверки контрактов", value=str(pending), inline=True)
    embed.set_footer(text="Автообновление: каждые 5 минут")
    return embed
