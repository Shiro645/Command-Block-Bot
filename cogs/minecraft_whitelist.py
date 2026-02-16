from __future__ import annotations

import json
import aiohttp
import re
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from utils.config import load_config


USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,16}$")


def staff_only():
    async def predicate(interaction: discord.Interaction) -> bool:
        cfg = load_config()
        staff_role_id = int(cfg["staff"]["role_id"])

        if interaction.guild is None:
            return False

        role = interaction.guild.get_role(staff_role_id)
        if role is None:
            return False

        member = interaction.user
        if not isinstance(member, discord.Member):
            member = await interaction.guild.fetch_member(interaction.user.id)

        return role in member.roles or member.guild_permissions.manage_guild

    return app_commands.check(predicate)


async def fetch_uuid(username: str) -> str | None:
    url = f"https://api.mojang.com/users/profiles/minecraft/{username}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            raw_uuid = data["id"]
            # format UUID with dashes
            return (
                f"{raw_uuid[0:8]}-"
                f"{raw_uuid[8:12]}-"
                f"{raw_uuid[12:16]}-"
                f"{raw_uuid[16:20]}-"
                f"{raw_uuid[20:]}"
            )


class MinecraftWhitelistCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _get_whitelist_path(self) -> Path:
        cfg = load_config()
        return Path(cfg["minecraft"]["whitelist_path"])

    def _load_whitelist(self, path: Path) -> list:
        if not path.exists():
            return []
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_whitelist(self, path: Path, data: list):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @app_commands.command(name="add_whitelist", description="Add a player to the Minecraft whitelist.")
    @staff_only()
    async def add_whitelist(self, interaction: discord.Interaction, username: str):
        if not USERNAME_RE.match(username):
            return await interaction.response.send_message("❌ Invalid username.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        uuid = await fetch_uuid(username)
        if uuid is None:
            return await interaction.followup.send("❌ Username not found (Mojang API).", ephemeral=True)

        path = self._get_whitelist_path()
        whitelist = self._load_whitelist(path)

        if any(entry["name"].lower() == username.lower() for entry in whitelist):
            return await interaction.followup.send("⚠️ Player already whitelisted.", ephemeral=True)

        whitelist.append({
            "uuid": uuid,
            "name": username
        })

        self._save_whitelist(path, whitelist)

        await interaction.followup.send(f"✅ **{username}** added to whitelist.", ephemeral=True)

    @app_commands.command(name="remove_whitelist", description="Remove a player from the Minecraft whitelist.")
    @staff_only()
    async def remove_whitelist(self, interaction: discord.Interaction, username: str):
        await interaction.response.defer(ephemeral=True)

        path = self._get_whitelist_path()
        whitelist = self._load_whitelist(path)

        new_list = [e for e in whitelist if e["name"].lower() != username.lower()]

        if len(new_list) == len(whitelist):
            return await interaction.followup.send("⚠️ Player not in whitelist.", ephemeral=True)

        self._save_whitelist(path, new_list)

        await interaction.followup.send(f"✅ **{username}** removed from whitelist.", ephemeral=True)

    @app_commands.command(name="check_whitelist", description="Check if a player is whitelisted.")
    @staff_only()
    async def check_whitelist(self, interaction: discord.Interaction, username: str):
        path = self._get_whitelist_path()
        whitelist = self._load_whitelist(path)

        is_whitelisted = any(e["name"].lower() == username.lower() for e in whitelist)

        await interaction.response.send_message(
            f"🔎 **{username}** is {'✅ WHITELISTED' if is_whitelisted else '❌ NOT whitelisted'}.",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(MinecraftWhitelistCog(bot))
