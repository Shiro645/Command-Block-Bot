from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils.config import load_config, save_config


class DiscordReactionRolesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _ensure_panel(self, guild: discord.Guild) -> None:
        cfg = load_config()
        rr = cfg["reaction_roles"]
        channel_id = int(rr["channel_id"])
        message_id = int(rr.get("message_id", 0) or 0)
        rr_map = rr.get("map", {})  # emoji -> role_id

        ch = guild.get_channel(channel_id)
        if ch is None or not isinstance(ch, discord.TextChannel):
            return
        if not rr_map:
            return

        # If message exists, do nothing
        if message_id:
            try:
                await ch.fetch_message(message_id)
                return
            except discord.NotFound:
                pass
            except discord.Forbidden:
                return

        # Post a new panel
        lines = []
        for emoji, role_id in rr_map.items():
            role = guild.get_role(int(role_id))
            if role:
                lines.append(f"{emoji} → {role.mention}")

        embed = discord.Embed(
            title="Choose your roles",
            description="\n".join(lines) if lines else "Configuration error.",
        )

        msg = await ch.send(embed=embed)

        for emoji in rr_map.keys():
            try:
                await msg.add_reaction(emoji)
            except discord.HTTPException:
                pass

        rr["message_id"] = msg.id
        save_config(cfg)

    @commands.Cog.listener()
    async def on_ready(self):
        # Auto-post only once per process start
        if not hasattr(self.bot, "_rr_autopost_done"):
            self.bot._rr_autopost_done = True
            for guild in self.bot.guilds:
                try:
                    await self._ensure_panel(guild)
                except Exception:
                    pass

    @app_commands.command(name="post_reaction_roles", description="Post the reaction roles message.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def post_reaction_roles(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return await interaction.response.send_message("⚠️ Guild not found.", ephemeral=True)

        await self._ensure_panel(interaction.guild)
        await interaction.response.send_message("✅ Reaction roles panel ensured.", ephemeral=True)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if self.bot.user and payload.user_id == self.bot.user.id:
            return

        cfg = load_config()
        rr = cfg.get("reaction_roles", {})
        if int(rr.get("message_id", 0) or 0) != payload.message_id:
            return

        role_id = rr.get("map", {}).get(str(payload.emoji))
        if not role_id or not payload.guild_id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        role = guild.get_role(int(role_id))
        if not role:
            return

        member = guild.get_member(payload.user_id)
        if member is None:
            try:
                member = await guild.fetch_member(payload.user_id)
            except discord.NotFound:
                return

        try:
            await member.add_roles(role, reason="Reaction role add")
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        cfg = load_config()
        rr = cfg.get("reaction_roles", {})
        if int(rr.get("message_id", 0) or 0) != payload.message_id:
            return

        role_id = rr.get("map", {}).get(str(payload.emoji))
        if not role_id or not payload.guild_id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        role = guild.get_role(int(role_id))
        if not role:
            return

        member = guild.get_member(payload.user_id)
        if member is None:
            try:
                member = await guild.fetch_member(payload.user_id)
            except discord.NotFound:
                return

        try:
            await member.remove_roles(role, reason="Reaction role remove")
        except discord.Forbidden:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(DiscordReactionRolesCog(bot))
