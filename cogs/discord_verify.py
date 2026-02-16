from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils.config import load_config


VERIFY_VIEW_CUSTOM_ID = "verify:accept_join"


class VerifyView(discord.ui.View):
    def __init__(self, player_role_id: int):
        super().__init__(timeout=None)
        self.player_role_id = player_role_id

    @discord.ui.button(
        label="Accept & Join",
        style=discord.ButtonStyle.success,
        custom_id=VERIFY_VIEW_CUSTOM_ID,
    )
    async def accept_and_join(self, interaction: discord.Interaction, _: discord.ui.Button):
        if interaction.guild is None:
            return await interaction.response.send_message("⚠️ Guild not found.", ephemeral=True)

        role = interaction.guild.get_role(self.player_role_id)
        if role is None:
            return await interaction.response.send_message("⚠️ Player role not found (wrong ID).", ephemeral=True)

        member = interaction.user
        if not isinstance(member, discord.Member):
            member = await interaction.guild.fetch_member(interaction.user.id)

        if role in member.roles:
            return await interaction.response.send_message("✅ You already have the **Player** role.", ephemeral=True)

        try:
            await member.add_roles(role, reason="Rules accepted / verification")
        except discord.Forbidden:
            return await interaction.response.send_message(
                "❌ I can't give this role (permissions / role hierarchy).",
                ephemeral=True,
            )

        await interaction.response.send_message("✅ Welcome! You now have the **Player** role.", ephemeral=True)


class DiscordVerifyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        cfg = load_config()
        self.rules_channel_id = int(cfg["verify"]["rules_channel_id"])
        self.player_role_id = int(cfg["verify"]["player_role_id"])

        self.bot.add_view(VerifyView(self.player_role_id))

    @app_commands.command(name="post_verify", description="Post the verification message in the rules channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def post_verify(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return await interaction.response.send_message("⚠️ Guild not found.", ephemeral=True)

        ch = interaction.guild.get_channel(self.rules_channel_id)
        if ch is None or not isinstance(ch, discord.TextChannel):
            return await interaction.response.send_message("⚠️ Invalid rules_channel_id.", ephemeral=True)

        embed = discord.Embed(
            title="Server Rules",
            description="Read the rules, then click **Accept & Join** to get the **Player** role.",
        )
        await ch.send(embed=embed, view=VerifyView(self.player_role_id))
        await interaction.response.send_message("✅ Verification message posted.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(DiscordVerifyCog(bot))
