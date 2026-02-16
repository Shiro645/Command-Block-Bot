from __future__ import annotations

import re
import discord
from discord import app_commands
from discord.ext import commands

from utils.config import load_config


TICKET_OPEN_CUSTOM_ID = "tickets:open"
TICKET_CLOSE_CUSTOM_ID = "tickets:close"
TICKET_TOPIC_PREFIX = "ticket_owner:"


def _slug(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9\- ]+", "", name)
    name = name.replace(" ", "-")
    name = re.sub(r"-{2,}", "-", name).strip("-")
    return name[:50] if name else "ticket"


class TicketOpenView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 Ouvrir un ticket", style=discord.ButtonStyle.primary, custom_id=TICKET_OPEN_CUSTOM_ID)
    async def open_ticket(self, interaction: discord.Interaction, _: discord.ui.Button):
        if interaction.guild is None:
            return await interaction.response.send_message("⚠️ Serveur introuvable.", ephemeral=True)

        cfg = load_config()
        category_id = int(cfg["tickets"]["category_id"])
        support_role_id = int(cfg["tickets"]["support_role_id"])

        category = interaction.guild.get_channel(category_id)
        if category is None or not isinstance(category, discord.CategoryChannel):
            return await interaction.response.send_message("⚠️ category_id invalide.", ephemeral=True)

        support_role = interaction.guild.get_role(support_role_id)
        if support_role is None:
            return await interaction.response.send_message("⚠️ support_role_id invalide.", ephemeral=True)

        member = interaction.user
        if not isinstance(member, discord.Member):
            member = await interaction.guild.fetch_member(interaction.user.id)

        # Empêche ticket dupliqué
        for ch in category.text_channels:
            if (ch.topic or "") == f"{TICKET_TOPIC_PREFIX}{member.id}":
                return await interaction.response.send_message(f"✅ Ton ticket existe déjà : {ch.mention}", ephemeral=True)

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            support_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        }

        channel = await category.create_text_channel(
            name=f"ticket-{_slug(member.name)}",
            topic=f"{TICKET_TOPIC_PREFIX}{member.id}",
            overwrites=overwrites,
            reason="Ticket created",
        )

        await channel.send(
            f"{member.mention} — explique ton problème ici.\n{support_role.mention}",
            view=TicketCloseView(),
        )

        await interaction.response.send_message(f"✅ Ticket créé : {channel.mention}", ephemeral=True)


class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Fermer le ticket", style=discord.ButtonStyle.danger, custom_id=TICKET_CLOSE_CUSTOM_ID)
    async def close_ticket(self, interaction: discord.Interaction, _: discord.ui.Button):
        if interaction.guild is None or interaction.channel is None:
            return await interaction.response.send_message("⚠️ Contexte invalide.", ephemeral=True)

        cfg = load_config()
        support_role_id = int(cfg["tickets"]["support_role_id"])
        support_role = interaction.guild.get_role(support_role_id)

        member = interaction.user
        if not isinstance(member, discord.Member):
            member = await interaction.guild.fetch_member(interaction.user.id)

        # autorisé: staff (support_role) OU owner (topic) OU manage_channels
        is_staff = support_role in member.roles if support_role else False
        is_owner = (interaction.channel.topic or "") == f"{TICKET_TOPIC_PREFIX}{member.id}"
        if not (is_staff or is_owner or member.guild_permissions.manage_channels):
            return await interaction.response.send_message("❌ Tu ne peux pas fermer ce ticket.", ephemeral=True)

        await interaction.response.send_message("🔒 Ticket fermé.", ephemeral=True)
        await interaction.channel.delete(reason=f"Ticket closed by {member} ({member.id})")


class DiscordTicketsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        cfg = load_config()
        self.panel_channel_id = int(cfg["tickets"]["panel_channel_id"])

        # persistent views
        self.bot.add_view(TicketOpenView())
        self.bot.add_view(TicketCloseView())

    @app_commands.command(name="post_ticket_panel", description="Poste le panel de tickets dans le salon prévu.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def post_ticket_panel(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return await interaction.response.send_message("⚠️ Serveur introuvable.", ephemeral=True)

        ch = interaction.guild.get_channel(self.panel_channel_id)
        if ch is None or not isinstance(ch, discord.TextChannel):
            return await interaction.response.send_message("⚠️ panel_channel_id invalide.", ephemeral=True)

        embed = discord.Embed(title="Support", description="Clique pour ouvrir un ticket.")
        await ch.send(embed=embed, view=TicketOpenView())
        await interaction.response.send_message("✅ Panel tickets posté.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(DiscordTicketsCog(bot))
