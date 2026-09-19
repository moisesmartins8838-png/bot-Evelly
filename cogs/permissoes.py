import os

import discord
from discord import app_commands
from discord.ext import commands

from database.database import (
    salvar_cargo_admin,
    pegar_cargo_admin,
    remover_cargo_admin,
)


def is_owner(user: discord.abc.User) -> bool:
    """Confere se o usuário é o dono definido no .env."""
    try:
        owner_id = int(os.getenv("OWNER_ID", "0"))
    except (TypeError, ValueError):
        owner_id = 0

    return user.id == owner_id


def is_discord_admin(user: discord.abc.User) -> bool:
    """Confere a permissão nativa Administrator do Discord."""
    if not isinstance(user, discord.Member):
        return False

    return user.guild_permissions.administrator


def is_admin_role(user: discord.abc.User) -> bool:
    """
    Confere se o usuário possui o cargo de administrador
    configurado para o servidor.
    """
    if not isinstance(user, discord.Member) or user.guild is None:
        return False

    role_id = pegar_cargo_admin(user.guild.id)

    if not role_id:
        return False

    return any(role.id == role_id for role in user.roles)


def is_admin(user: discord.abc.User) -> bool:
    """
    Administrador = Administrator do Discord OU cargo administrativo
    configurado pelo dono da Evelly.
    """
    return is_discord_admin(user) or is_admin_role(user)


def pode_controlar_evelly(user: discord.abc.User) -> bool:
    """Permissão usada pelos sistemas administrativos da Evelly."""
    return is_owner(user) or is_admin(user)


def nivel_permissao(user: discord.abc.User) -> str:
    if is_owner(user):
        return "OWNER"

    if is_discord_admin(user):
        return "ADMINISTRATOR"

    if is_admin_role(user):
        return "ADMIN_ROLE"

    return "USER"


class Permissoes(commands.Cog):
    """
    Sistema de permissões administrativas da Evelly.

    O dono da Evelly pode configurar um cargo por servidor.
    Quem possuir esse cargo poderá controlar os sistemas que
    utilizam pode_controlar_evelly().
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="cargo_admin",
        description="Define o cargo que terá acesso administrativo à Evelly.",
    )
    @app_commands.describe(
        cargo="Cargo que poderá controlar os sistemas administrativos da Evelly."
    )
    async def cargo_admin(
        self,
        interaction: discord.Interaction,
        cargo: discord.Role,
    ):
        if not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Apenas o proprietário da Evelly pode definir o cargo administrativo.",
                ephemeral=True,
            )
            return

        if cargo.is_default():
            await interaction.response.send_message(
                "❌ O cargo @everyone não pode ser usado.",
                ephemeral=True,
            )
            return

        if cargo.managed:
            await interaction.response.send_message(
                "❌ Esse é um cargo gerenciado pelo Discord e não pode ser usado.",
                ephemeral=True,
            )
            return

        if not salvar_cargo_admin(interaction.guild.id, cargo.id):
            await interaction.response.send_message(
                "❌ Não consegui salvar o cargo no Supabase. Veja o console da Evelly.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"🛡️ Cargo administrativo definido como {cargo.mention}.\n\n"
            "Quem possuir esse cargo poderá usar os sistemas administrativos "
            "da Evelly que utilizam a permissão de administrador.",
            ephemeral=True,
        )

    @app_commands.command(
        name="cargo_admin_status",
        description="Mostra o cargo administrativo configurado para a Evelly.",
    )
    async def cargo_admin_status(self, interaction: discord.Interaction):
        if not pode_controlar_evelly(interaction.user):
            await interaction.response.send_message(
                "❌ Você não possui permissão para consultar as configurações administrativas.",
                ephemeral=True,
            )
            return

        role_id = pegar_cargo_admin(interaction.guild.id)

        if not role_id:
            await interaction.response.send_message(
                "🛡️ Nenhum cargo administrativo personalizado está configurado.",
                ephemeral=True,
            )
            return

        role = interaction.guild.get_role(role_id)

        if role is None:
            await interaction.response.send_message(
                f"⚠️ O cargo configurado não existe mais no servidor.\nID: `{role_id}`",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"🛡️ Cargo administrativo atual: {role.mention}",
            ephemeral=True,
        )

    @app_commands.command(
        name="cargo_admin_remover",
        description="Remove o cargo administrativo personalizado da Evelly.",
    )
    async def cargo_admin_remover(self, interaction: discord.Interaction):
        if not is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Apenas o proprietário da Evelly pode remover o cargo administrativo.",
                ephemeral=True,
            )
            return

        if not remover_cargo_admin(interaction.guild.id):
            await interaction.response.send_message(
                "❌ Não consegui remover o cargo do Supabase.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "🛡️ Cargo administrativo personalizado removido.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Permissoes(bot))
    print("🛡️ Sistema de permissões carregado com sucesso.", flush=True)
