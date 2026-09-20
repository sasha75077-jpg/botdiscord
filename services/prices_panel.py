"""Автопанель прайса: постинг, обновление, закреп, переезд между каналами.

Настройки (guild_settings, тянутся с сайта pull-ем):
- prices_panel_channel_id - куда постить
- prices_panel_message_id - что обновлять
- prices_panel_posted_channel_id - где реально висит (для переезда)
"""
import discord

from database import execute, fetch_one, get_setting, set_setting

CH_KEY = "prices_panel_channel_id"
MSG_KEY = "prices_panel_message_id"
POSTED_CH_KEY = "prices_panel_posted_channel_id"


async def _get_cfg(guild_id: str):
    ch = await get_setting(CH_KEY, guild_id)
    if not ch:
        ch = await get_setting("prices_channel_id")  # старый глобальный ключ
    msg = await get_setting(MSG_KEY, guild_id)
    if not msg:
        msg = await get_setting("prices_message_id")
    posted = await get_setting(POSTED_CH_KEY, guild_id)
    return (ch or "").strip(), (msg or "").strip(), (posted or "").strip()


async def ensure_panel(bot, guild: discord.Guild, build_embed) -> str:
    """Проверить/обновить панель. Возвращает статус: ok/posted/moved/no-channel."""
    gid = str(guild.id)
    ch_id, msg_id, posted_ch = await _get_cfg(gid)
    if not ch_id or not ch_id.isdigit():
        return "no-channel"

    channel = guild.get_channel(int(ch_id))
    if channel is None:
        try:
            channel = await guild.fetch_channel(int(ch_id))
        except Exception:
            return "no-channel"

    # Переезд: висела в другом канале - удалить там
    if posted_ch and posted_ch != ch_id and msg_id:
        try:
            old_ch = guild.get_channel(int(posted_ch))
            if old_ch is None:
                old_ch = await guild.fetch_channel(int(posted_ch))
            old_msg = await old_ch.fetch_message(int(msg_id))
            await old_msg.delete()
        except Exception:
            pass
        msg_id = ""
        await set_setting(MSG_KEY, "", gid)

    msg = None
    if msg_id and msg_id.isdigit():
        try:
            msg = await channel.fetch_message(int(msg_id))
        except Exception:
            msg = None

    embed = await build_embed()

    if msg is None:
        msg = await channel.send(embed=embed)
        try:
            await msg.pin()
        except Exception:
            pass
        await set_setting(MSG_KEY, str(msg.id), gid)
        await set_setting(POSTED_CH_KEY, str(channel.id), gid)
        return "posted"

    try:
        old = msg.embeds[0].to_dict() if msg.embeds else {}
        if old != embed.to_dict():
            await msg.edit(embed=embed)
    except Exception as e:
        print(f"[prices-panel] warn edit: {e}")
    try:
        if not msg.pinned:
            await msg.pin()
    except Exception:
        pass
    if posted_ch != str(channel.id):
        await set_setting(POSTED_CH_KEY, str(channel.id), gid)
    return "ok"
