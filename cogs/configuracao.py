import discord

from discord import app_commands
from discord.ext import commands

from database.database import (
    criar_servidor,
    pegar_servidor
)


class Configuracao(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="config",
        description="Mostra as configurações da Evelly."
    )
    async def config(
        self,
        interaction: discord.Interaction
    ):

        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Este comando só pode ser usado em um servidor.",
                ephemeral=True
            )
            return

        guild_id = interaction.guild.id

        criar_servidor(guild_id)

        servidor = pegar_servidor(guild_id)

        canal = servidor[1]
        cargo = servidor[2]
        mensagem = servidor[3]
        youtube = servidor[4]
        boas_vindas = servidor[5]

        canal_texto = (
            f"<#{canal}>"
            if canal
            else "❌ Não configurado"
        )

        cargo_texto = (
            f"<@&{cargo}>"
            if cargo
            else "❌ Não configurado"
        )

        youtube_texto = (
            "🟢 Ativado"
            if youtube
            else "🔴 Desativado"
        )

        boas_vindas_texto = (
            "🟢 Ativado"
            if boas_vindas
            else "🔴 Desativado"
        )

        mensagem_texto = (
            mensagem
            if mensagem
            else "Padrão da Evelly"
        )

        embed = discord.Embed(
            title="⚙️ Configuração da Evelly",
            description=(
                "Aqui estão as configurações atuais "
                "deste servidor."
            ),
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="🎬 YouTube",
            value=youtube_texto,
            inline=True
        )

        embed.add_field(
            name="👋 Boas-vindas",
            value=boas_vindas_texto,
            inline=True
        )

        embed.add_field(
            name="📢 Canal de anúncios",
            value=canal_texto,
            inline=False
        )

        embed.add_field(
            name="🔔 Cargo de notificação",
            value=cargo_texto,
            inline=False
        )

        embed.add_field(
            name="💬 Mensagem do YouTube",
            value=mensagem_texto,
            inline=False
        )

        await interaction.response.send_message(
            embed=embed
        )


async def setup(bot):
    await bot.add_cog(Configuracao(bot))