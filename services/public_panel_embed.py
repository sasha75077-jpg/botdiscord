import discord
from database import fetch_one, get_setting

MEL_ROLE_ID = 1316909791389679719


def _parse_ids(s):
    return {x.strip() for x in (s or "").split(",") if x.strip().isdigit()}


async def build_public_panel_embed(guild: discord.Guild) -> discord.Embed:
    fam_raw = await get_setting("family_member_role_ids", str(guild.id))
    fam_ids = _parse_ids(fam_raw)
    members = []
    if fam_ids:
        seen = set()
        for rid in fam_ids:
            role = guild.get_role(int(rid))
            if role is None:
                continue
            for m in role.members:
                if m.id not in seen:
                    seen.add(m.id)
                    members.append(m)
    else:
        role = guild.get_role(MEL_ROLE_ID)
        members = list(role.members) if role else []

    total = len(members)

    online_statuses = {discord.Status.online, discord.Status.idle, discord.Status.dnd}
    online = sum(1 for m in members if m.status in online_statuses)

    row = await fetch_one(
        "SELECT COUNT(*) AS cnt FROM contracts WHERE confirm_status='PENDING' AND (? IS NULL OR guild_id = ?)",
        (str(guild.id), str(guild.id)))

    pending = int(row["cnt"] or 0) if row else 0

    embed = discord.Embed(
        title="Панель игрока",
        description="Нажми кнопку ниже — профиль откроется только тебе.",
        color=0x3498DB
    )
    embed.add_field(name="Семья в сети", value=str(online), inline=True)
    embed.add_field(name="Семья (всего)", value=str(total), inline=True)
    embed.add_field(name="Ожидание проверки контрактов", value=str(pending), inline=True)
    embed.set_footer(text="Автообновление: каждые 5 минут")
    return embed
