import discord
from database import fetch_one, execute, get_setting, set_setting

PENDING_MSG_KEY = "pending_counter_message_id"

async def upsert_pending_counter_message(bot: discord.Client, content: str, guild_id: str):
    """
    Обновить или создать сообщение со счетчиком ожидающих контрактов

    Args:
        bot: Discord клиент
        content: Текст сообщения
        guild_id: ID сервера Discord
    """
    # Получить ID сообщения для этого сервера (из guild_settings)
    msg_id_str = await get_setting(PENDING_MSG_KEY, guild_id)
    msg_id = int(msg_id_str) if msg_id_str else None

    # Получить канал для этого сервера
    channel_id_str = await get_setting("pending_counter_channel_id", guild_id)
    if not channel_id_str:
        # Попробовать использовать admin_contracts_channel_id как fallback
        channel_id_str = await get_setting("admin_contracts_channel_id", guild_id)

    if not channel_id_str:
        print(f"[Guild {guild_id}] pending_counter_channel_id не настроен")
        return None

    channel_id = int(channel_id_str)
    channel = bot.get_channel(channel_id)

    if not channel:
        try:
            channel = await bot.fetch_channel(channel_id)
        except Exception as e:
            print(f"[Guild {guild_id}] Не удалось получить канал {channel_id}: {e}")
            return None

    # Обновить существующее сообщение или создать новое
    if msg_id:
        try:
            msg = await channel.fetch_message(msg_id)
            await msg.edit(content=content)
            return msg.id
        except discord.NotFound:
            pass

    msg = await channel.send(content=content)

    # Сохранить ID сообщения для этого сервера
    await set_setting(PENDING_MSG_KEY, str(msg.id), guild_id)

    return msg.id


