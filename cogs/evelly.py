import discord
from discord import app_commands
from discord.ext import commands

from cogs.permissoes import pode_controlar_evelly


PURPLE = 0x8E44AD


class Evelly(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="evelly",
        description="Abre o painel central da Evelly.",
    )
    async def evelly(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="💜 Evelly • Central",
            description=(
                "Use a central da Evelly para encontrar os sistemas "
                "sem precisar decorar vários comandos.\n\n"
                "🎫 **Tickets**\n"
                "`/ticket configurar` • `/ticket painel`\n\n"
                "💡 **Sugestões**\n"
                "`/sugestao configurar` • `/sugestao painel`\n\n"
                "📨 **Automação**\n"
                "`/automsg` • `/automsg_deletar`\n\n"
                "🛡️ **Administração**\n"
                "`/cargo_admin` • configurações administrativas\n\n"
                "📺 **YouTube / Comunidade**\n"
                "Use os comandos específicos desses sistemas."
            ),
            color=PURPLE,
        )
        embed.set_footer(
            text="Evelly • Central de comandos"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(Evelly(bot))
    print("💜 cogs.evelly carregado com sucesso", flush=True)
