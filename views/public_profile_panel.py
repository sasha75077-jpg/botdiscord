import discord
from discord.ui import View
from services.profile_panel import open_profile_panel

class PublicProfilePanelView(View):
    def __init__(self):
        super().__init__(timeout=None)  # persistent

    @discord.ui.button(
        label="Открыть профиль",
        style=discord.ButtonStyle.primary,
        custom_id="publicpanel:open_profile"
    )
    async def open_profile_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await open_profile_panel(interaction)  # шлёт новый ephemeral профиль
