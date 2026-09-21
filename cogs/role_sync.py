"""Ког сверки панельных ролей с Discord-ролями."""
import discord
from discord.ext import commands, tasks

from services import role_sync as rs


class RoleSync(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        if not self.reconcile_loop.is_running():
            self.reconcile_loop.start()
        if not self.contracts_poll_loop.is_running():
            self.contracts_poll_loop.start()
        if not self.contracts_nudge_loop.is_running():
            self.contracts_nudge_loop.start()
        if not self.prices_loop.is_running():
            self.prices_loop.start()

    @tasks.loop(minutes=10)
    async def reconcile_loop(self):
        for guild in self.bot.guilds:
            try:
                await rs.pull_remote_state(str(guild.id))
            except Exception as e:
                print(f"[role-sync] warn pull {guild.id}: {e}")
            try:
                await rs.pull_ranks(str(guild.id))
            except Exception as e:
                print(f"[ranks-pull] warn {guild.id}: {e}")
            try:
                await rs.push_users(str(guild.id))
            except Exception as e:
                print(f"[users-push] warn {guild.id}: {e}")
            try:
                await rs.reconcile_guild(self.bot, guild)
            except Exception as e:
                print(f"[role-sync] warn guild {guild.id}: {e}")

    @reconcile_loop.before_loop
    async def _before_reconcile(self):
        await self.bot.wait_until_ready()

    @tasks.loop(seconds=60)
    async def contracts_poll_loop(self):
        try:
            await rs.poll_site_contracts(self.bot)
        except Exception as e:
            print(f"[contracts-poll] warn: {e}")
        try:
            await rs.poll_site_bonus(self.bot)
        except Exception as e:
            print(f"[bonus-poll] warn: {e}")
        try:
            await rs.poll_panel_tasks(self.bot)
        except Exception as e:
            print(f"[panels] warn: {e}")

    @contracts_poll_loop.before_loop
    async def _before_contracts_poll(self):
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=10)
    async def contracts_nudge_loop(self):
        try:
            await rs.nudge_site_contracts(self.bot)
        except Exception as e:
            print(f"[contracts-nudge] warn: {e}")

    @contracts_nudge_loop.before_loop
    async def _before_contracts_nudge(self):
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=5)
    async def prices_loop(self):
        try:
            from services.prices_sync import pull_prices
            from services.prices_panel import ensure_panel
            from cogs.admin_panel import build_prices_embed
            await pull_prices()
            for guild in list(self.bot.guilds):
                try:
                    await ensure_panel(self.bot, guild, build_prices_embed)
                except Exception as e:
                    print(f"[prices-panel] warn {guild.id}: {e}")
        except Exception as e:
            print(f"[prices] warn loop: {e}")

    @prices_loop.before_loop
    async def _before_prices(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        try:
            if {r.id for r in before.roles} == {r.id for r in after.roles}:
                return
            await rs.reconcile_member(self.bot, after.guild, after)
        except Exception as e:
            print(f"[role-sync] warn member_update: {e}")

    @discord.app_commands.command(name="sync_roles", description="Сверить панельные роли с Discord-ролями сейчас")
    async def sync_roles_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not interaction.guild:
            return await interaction.followup.send("❌ Только на сервере.", ephemeral=True)
        try:
            await rs.pull_remote_state(str(interaction.guild.id))
            n = await rs.reconcile_guild(self.bot, interaction.guild)
            await interaction.followup.send(f"✅ Сверка готова, изменений: {n}.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Ошибка: {e}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(RoleSync(bot))
