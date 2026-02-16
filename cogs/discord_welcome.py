from __future__ import annotations

import discord
from discord.ext import commands

from utils.config import load_config


class DiscordWelcomeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        cfg = load_config()
        self.channel_id = int(cfg["welcome"]["channel_id"])

    def _channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        ch = guild.get_channel(self.channel_id)
        return ch if isinstance(ch, discord.TextChannel) else None

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        ch = self._channel(member.guild)
        if ch:
            await ch.send(f"👋 Welcome {member.mention}!\nHere take a seat before you join the adventure.\nHere you will be able to make friends and seek help.")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        ch = self._channel(member.guild)
        if ch:
            await ch.send(f"👋 **{member.name}** left the server.\nHope we see you again soon")


async def setup(bot: commands.Bot):
    await bot.add_cog(DiscordWelcomeCog(bot))
