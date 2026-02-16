from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from mcstatus import JavaServer

from utils.config import load_config


class MinecraftCoreCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="server_status", description="Show the Minecraft server status.")
    async def server_status(self, interaction: discord.Interaction):
        cfg = load_config()
        host = cfg["minecraft"]["server_host"]
        port = int(cfg["minecraft"]["server_port"])

        await interaction.response.defer(thinking=True)

        try:
            server = JavaServer(host, port)
            status = await server.async_status()

            players_online = status.players.online
            players_max = status.players.max
            latency = round(status.latency)

            desc = f"✅ **Online**\nPlayers: **{players_online}/{players_max}**\nPing: **{latency} ms**"
            embed = discord.Embed(title="Minecraft Server Status", description=desc)
            await interaction.followup.send(embed=embed)

        except Exception:
            embed = discord.Embed(
                title="Minecraft Server Status",
                description="❌ **Offline** (or unreachable from the bot).",
            )
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="ip", description="Show how to join the Minecraft server.")
    async def ip(self, interaction: discord.Interaction):
        cfg = load_config()
        text = cfg["minecraft"]["public_ip_text"]
        await interaction.response.send_message(text, ephemeral=True)

    @app_commands.command(name="modpacks", description="Show the modpack info / download link.")
    async def modpacks(self, interaction: discord.Interaction):
        cfg = load_config()
        text = cfg["minecraft"]["modpack_text"]
        await interaction.response.send_message(text, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(MinecraftCoreCog(bot))
