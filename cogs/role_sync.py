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

    @tasks.loop(minutes=10)
    async def reconcile_loop(self):
        for guild in self.bot.guilds:
            try:
                await rs.pull_remote_state(str(guild.id))
            except Exception as e:
                print(f"[role-sync] warn pull {guild.id}: {e}")
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
            await rs.poll_site_contracts()
        except Exception as e:
            print(f"[contracts-poll] warn: {e}")

    @contracts_poll_loop.before_loop
    async def _before_contracts_poll(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        try:
            if {r.id for r in before.roles} == {r.id for r in after.roles}:
                return
            await rs.reconcile_member(self.bot, after.guild, after)
        except Exception as e:
            print(f"[role-sync] warn member_update: {e}")


async def setup(bot):
    await bot.add_cog(RoleSync(bot))
