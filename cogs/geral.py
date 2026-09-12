import discord

from discord import app_commands
from discord.ext import commands


class Geral(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="ping",
        description="Mostra a latência da Evelly."
    )
    async def ping(self, interaction: discord.Interaction):

        latencia = round(self.bot.latency * 1000)

        await interaction.response.send_message(
            f"🏓 **Pong!**\n"
            f"📡 Latência: `{latencia}ms`"
        )

    @app_commands.command(
        name="avatar",
        description="Mostra o avatar de um usuário."
    )
    @app_commands.describe(
        usuario="Usuário que deseja visualizar."
    )
    async def avatar(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member | None = None
    ):

        usuario = usuario or interaction.user

        embed = discord.Embed(
            title=f"🖼️ Avatar de {usuario.display_name}",
            color=discord.Color.blurple()
        )

        embed.set_image(
            url=usuario.display_avatar.url
        )

        await interaction.response.send_message(
            embed=embed
        )

    @app_commands.command(
        name="serverinfo",
        description="Mostra informações do servidor."
    )
    async def serverinfo(
        self,
        interaction: discord.Interaction
    ):

        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message(
                "❌ Este comando só pode ser usado em um servidor.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📊 Informações do servidor",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="🏠 Nome",
            value=guild.name,
            inline=False
        )

        embed.add_field(
            name="🆔 ID",
            value=str(guild.id),
            inline=True
        )

        embed.add_field(
            name="👥 Membros",
            value=str(guild.member_count),
            inline=True
        )

        embed.add_field(
            name="📅 Criado em",
            value=discord.utils.format_dt(
                guild.created_at,
                style="D"
            ),
            inline=False
        )

        if guild.icon:
            embed.set_thumbnail(
                url=guild.icon.url
            )

        await interaction.response.send_message(
            embed=embed
        )


async def setup(bot):
    await bot.add_cog(Geral(bot))