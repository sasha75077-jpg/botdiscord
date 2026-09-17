import discord
from discord.ui import View, Button
from database import get_setting

PING_ROLE_KEY = "contracts_ping_role_id"
PING_CHANNEL_KEY = "contracts_ping_channel_id"

 
async def send_ping(client: discord.Client, role_id: int, channel_id: int, text: str):
    channel = client.get_channel(channel_id) or await client.fetch_channel(channel_id)
    await channel.send(
        f"<@&{role_id}> {text}",
        allowed_mentions=discord.AllowedMentions(roles=True)
    )


# ---- Товары с самолета ----

class GoodsView(View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="📦 Погрузка", style=discord.ButtonStyle.success)
    async def loading_btn(self, interaction: discord.Interaction, button: Button):
        await _do_ping(interaction,
            "Начинаем грузить **Товары с самолета** — присоединяйтесь!\n"
            "Найти контракт: **F3 → Семейные контракты → Погрузка товаров**"
        )

    @discord.ui.button(label="🚚 Сдача", style=discord.ButtonStyle.primary)
    async def delivery_btn(self, interaction: discord.Interaction, button: Button):
        await _do_ping(interaction,
            "Сдаём **Товары с самолета** — присоединяйтесь!\n"
            "Найти контракт: **F3 → Семейные контракты → Сдача контракта**"
        )

    @discord.ui.button(label="🔒 Закрыто", style=discord.ButtonStyle.danger)
    async def closed_btn(self, interaction: discord.Interaction, button: Button):
        await _do_ping(interaction, "Контракт **Товары с самолета** завершён. Спасибо всем! Для подачи отчета необходимо использовать данную [ссылку](https://rapid-glitter-d42f.sasha75077.workers.dev/), либо же вторую у кого плохо работает [ссылка](https://script.google.com/macros/s/AKfycbwURFEMMiRsUswjEfJRrTdqVcvgm284HCE6zbdEWYQyZui7QDyxCF6SGRoUg2wwQAwegw/exec)")

    @discord.ui.button(label="⬅️ Назад", style=discord.ButtonStyle.secondary)
    async def back_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(
            embed=discord.Embed(title="📣 Пинг контрактов", description="Выберите контракт:", color=0x9B7BFF),
            view=ContractsPingView()
        )


# ---- Ателье ----

class AtelierView(View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="🧵 Шить", style=discord.ButtonStyle.success)
    async def sew_btn(self, interaction: discord.Interaction, button: Button):
        await _do_ping(interaction,
            "**Ателье активировано** — начинаем шить, присоединяйтесь!\n"
            "Найти контракт: **F3 → Семейные контракты → Ателье**"
        )

    @discord.ui.button(label="🔒 Закрыто", style=discord.ButtonStyle.danger)
    async def closed_btn(self, interaction: discord.Interaction, button: Button):
        await _do_ping(interaction, "Контракт **Ателье** завершён. Спасибо всем! Для подачи отчета необходимо использовать данную [ссылку](https://rapid-glitter-d42f.sasha75077.workers.dev/), либо же вторую у кого плохо работает [ссылка](https://script.google.com/macros/s/AKfycbwURFEMMiRsUswjEfJRrTdqVcvgm284HCE6zbdEWYQyZui7QDyxCF6SGRoUg2wwQAwegw/exec)")

    @discord.ui.button(label="⬅️ Назад", style=discord.ButtonStyle.secondary)
    async def back_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(
            embed=discord.Embed(title="📣 Пинг контрактов", description="Выберите контракт:", color=0x9B7BFF),
            view=ContractsPingView()
        )


# ---- Металлургия сдача ----

class MetallurgyView(View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="⛏️ Сдача", style=discord.ButtonStyle.success)
    async def delivery_btn(self, interaction: discord.Interaction, button: Button):
        await _do_ping(interaction,
            "**Металлургия сдача активирована** — приезжайте на точку сдачи!\n"
            "Найти контракт: **F3 → Семейные контракты → Точка сдачи Металлургии**"
        )

    @discord.ui.button(label="🔒 Закрыто", style=discord.ButtonStyle.danger)
    async def closed_btn(self, interaction: discord.Interaction, button: Button):
        await _do_ping(interaction, "Контракт **Металлургия** завершён. Спасибо всем! Для подачи отчета необходимо использовать данную [ссылку](https://rapid-glitter-d42f.sasha75077.workers.dev/), либо же вторую у кого плохо работает [ссылка](https://script.google.com/macros/s/AKfycbwURFEMMiRsUswjEfJRrTdqVcvgm284HCE6zbdEWYQyZui7QDyxCF6SGRoUg2wwQAwegw/exec)")

    @discord.ui.button(label="⬅️ Назад", style=discord.ButtonStyle.secondary)
    async def back_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(
            embed=discord.Embed(title="📣 Пинг контрактов", description="Выберите контракт:", color=0x9B7BFF),
            view=ContractsPingView()
        )


# ---- Главное меню пинга ----

class ContractsPingView(View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="✈️ Товары с самолета", style=discord.ButtonStyle.primary)
    async def goods_btn(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(title="✈️ Товары с самолета", description="Выберите действие:", color=0x3498DB)
        await interaction.response.edit_message(embed=embed, view=GoodsView())

    @discord.ui.button(label="🧵 Ателье", style=discord.ButtonStyle.primary)
    async def atelier_btn(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(title="🧵 Ателье", description="Выберите действие:", color=0x3498DB)
        await interaction.response.edit_message(embed=embed, view=AtelierView())

    @discord.ui.button(label="⛏️ Металлургия сдача", style=discord.ButtonStyle.primary)
    async def metallurgy_btn(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(title="⛏️ Металлургия сдача", description="Выберите действие:", color=0x3498DB)
        await interaction.response.edit_message(embed=embed, view=MetallurgyView())

    @discord.ui.button(label="⬅️ Назад", style=discord.ButtonStyle.secondary)
    async def back_btn(self, interaction: discord.Interaction, button: Button):
        from cogs.admin_panel import AdminMainView
        embed = discord.Embed(title="Админ-панель", description="Выберите раздел:", color=0x9B7BFF)
        await interaction.response.edit_message(embed=embed, view=AdminMainView())


async def _do_ping(interaction: discord.Interaction, text: str):
    role_raw = await get_setting(PING_ROLE_KEY)
    channel_raw = await get_setting(PING_CHANNEL_KEY)

    if not role_raw or not channel_raw:
        await interaction.response.send_message(
            "❌ Не настроены `contracts_ping_role_id` или `contracts_ping_channel_id` в настройках.",
            ephemeral=True
        )
        return

    role_id = int(role_raw)
    channel_id = int(channel_raw)

    await send_ping(interaction.client, role_id, channel_id, text)
    await interaction.response.send_message("✅ Пинг отправлен!", ephemeral=True)


async def show_contracts_ping(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📣 Пинг контрактов",
        description="Выберите контракт:",
        color=0x9B7BFF
    )
    await interaction.response.edit_message(embed=embed, view=ContractsPingView())
