from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


EMOJI = {
    "emerald": "<:emerald:1472479098055164145>",
    "stick": "<:stick:1472472154175049880>",
    "gold": "<:gold:1472472602957058139>",
    "iron": "<:iron:1472469042802462770>",
    "diamond": "<:diamond:1472472278695678108>",
    "netherite": "<:netherite:1472500827385102407>",
}


class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help", description="Show all available commands.")
    async def help(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title="Server Commands",
            description="Here are all available commands:",
            color=discord.Color.blurple(),
        )

        # 📦 Economy
        embed.add_field(
            name="Mining & Inventory",
            value=(
                "`/inventory` → Show your blocks, items and gear\n"
                "`/sell` → Sell all your blocks\n"
                "`/market` → Open the market\n"
            ),
            inline=False,
        )

        # 🛠 Craft
        embed.add_field(
            name="Crafting",
            value=(
                "`/craft <item> <material>` → Craft gear\n"
                "`/craftlist` → Show all recipes\n"
            ),
            inline=False,
        )

        # ⭐ XP & Talents
        embed.add_field(
            name="XP & Talents",
            value=(
                "`/xp` → Show your level and XP\n"
                "`/talents` → Show talent branches\n"
                "`/talent_buy <branch> <points>` → Spend talent points\n"
            ),
            inline=False,
        )

        # 👑 Admin
        embed.add_field(
            name="Admin Commands",
            value=(
                "`/add_block`\n"
                "`/add_emerald`\n"
                "`/add_item`\n"
                "`/add_gear`\n"
            ),
            inline=False,
        )

        embed.set_footer(text="More features coming soon...")

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))
