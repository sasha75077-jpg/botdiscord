import discord

async def open_profile_panel(interaction: discord.Interaction):
    from cogs.user_panel import build_profile_embed, get_rank_name_from_discord, MainPanelView

    guild = interaction.guild
    member = interaction.user if isinstance(interaction.user, discord.Member) else guild.get_member(interaction.user.id)
    if member is None:
        member = await guild.fetch_member(interaction.user.id)

    rank_name = await get_rank_name_from_discord(member)
    embed = await build_profile_embed(str(member.id), str(guild.id))

    for i, f in enumerate(embed.fields):
        if f.name == "Ранг":
            embed.set_field_at(i, name="Ранг", value=rank_name, inline=True)
            break
    else:
        embed.add_field(name="Ранг", value=rank_name, inline=True)

    if not any(f.name == "Discord ID" for f in embed.fields):
        embed.add_field(name="Discord ID", value=f"`{member.id}`", inline=False)

    await interaction.response.send_message(
        embed=embed,
        view=MainPanelView(),
        ephemeral=True
    )
