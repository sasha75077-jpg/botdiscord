import discord
from discord.ext import commands, tasks
from datetime import datetime, timezone, timedelta

MSK = timezone(timedelta(hours=3))

CHANNEL_ID = 1323994399767658546
ROLE_ID = 1446803323045937264

MSG_18 = """<@&{role}> 

Ребята, сегодня **день подачи на премию**! 🎉

Кто на этой неделе закидывал скриншоты и они были приняты — вы получите за это денюшку 💰

Для подачи:
1. Перейдите в канал: https://discord.com/channels/880440495233454080/1472952119521710091
2. Откройте свой профиль
⚠️ Если не указали свой статик ID — **обязательно укажите**, иначе нельзя будет подать отчёт на премию
3. Нажмите **Премия** → **Отправить**

Перед отправкой проверьте: сумма и контракты актуальны ли они ✅"""

MSG_20 = """<@&{role}> 

⏰ **Напоминание!** Приём премий скоро заканчивается!

Кто ещё не подал — у вас последний шанс 🔔

Для подачи:
1. Перейдите в канал: https://discord.com/channels/880440495233454080/1472952119521710091
2. Откройте свой профиль и нажмите **Премия** → **Отправить**

Кто забудет подать — увы, не сможем посчитать вашу премию 😔"""


class BonusReminder(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._sent_18 = None
        self._sent_20 = None
        self.reminder_loop.start()

    def cog_unload(self):
        self.reminder_loop.cancel()

    @tasks.loop(minutes=1)
    async def reminder_loop(self):
        now = datetime.now(MSK)
        if now.weekday() != 6:  # 6 = воскресенье
            return

        today = now.date()
        channel = self.bot.get_channel(CHANNEL_ID) or await self.bot.fetch_channel(CHANNEL_ID)

        if now.hour == 18 and now.minute == 0 and self._sent_18 != today:
            self._sent_18 = today
            await channel.send(
                MSG_18.format(role=ROLE_ID),
                allowed_mentions=discord.AllowedMentions(roles=True)
            )

        if now.hour == 20 and now.minute == 0 and self._sent_20 != today:
            self._sent_20 = today
            await channel.send(
                MSG_20.format(role=ROLE_ID),
                allowed_mentions=discord.AllowedMentions(roles=True)
            )

    @reminder_loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(BonusReminder(bot))
