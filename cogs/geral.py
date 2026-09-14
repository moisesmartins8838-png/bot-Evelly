import time

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
        inicio = time.monotonic()

        agora = discord.utils.utcnow()
        criado = interaction.created_at

        atraso = (agora - criado).total_seconds()

        print("=" * 60, flush=True)
        print("[PING DEBUG] INTERAÇÃO RECEBIDA", flush=True)
        print(f"[PING DEBUG] criado : {criado.isoformat()}", flush=True)
        print(f"[PING DEBUG] agora   : {agora.isoformat()}", flush=True)
        print(f"[PING DEBUG] atraso  : {atraso:.3f}s", flush=True)
        print(
            f"[PING DEBUG] latency : "
            f"{self.bot.latency * 1000:.0f}ms",
            flush=True
        )

        try:
            print("[PING DEBUG] enviando resposta...", flush=True)

            await interaction.response.send_message(
                f"🏓 **Pong!**\n"
                f"📡 Latência: `{round(self.bot.latency * 1000)}ms`"
            )

            fim = time.monotonic()

            print(
                f"[PING DEBUG] resposta enviada em "
                f"{fim - inicio:.3f}s",
                flush=True
            )

            print("=" * 60, flush=True)

        except Exception as e:
            fim = time.monotonic()

            print(
                f"[PING DEBUG] FALHOU após "
                f"{fim - inicio:.3f}s",
                flush=True
            )

            print(
                f"[PING DEBUG] tipo: "
                f"{type(e).__name__}",
                flush=True
            )

            print(
                f"[PING DEBUG] erro: "
                f"{e!r}",
                flush=True
            )

            print(
                f"[PING DEBUG] response.is_done(): "
                f"{interaction.response.is_done()}",
                flush=True
            )

            print("=" * 60, flush=True)

            raise

    @app_commands.command(
        name="avatar",
        description="Mostra seu avatar ou o de outro usuário."
    )
    @app_commands.describe(
        usuario="Usuário cujo avatar deseja visualizar."
    )
    async def avatar(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member | None = None
    ):
        usuario = usuario or interaction.user

        embed = discord.Embed(
            title=f"Avatar de {usuario.display_name}"
        )

        embed.set_image(url=usuario.display_avatar.url)

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
            title=f"📊 Informações de {guild.name}"
        )

        embed.add_field(
            name="👑 Dono",
            value=str(guild.owner),
            inline=False
        )

        embed.add_field(
            name="👥 Membros",
            value=str(guild.member_count),
            inline=True
        )

        embed.add_field(
            name="🆔 ID",
            value=str(guild.id),
            inline=True
        )

        await interaction.response.send_message(
            embed=embed
        )


async def setup(bot):
    await bot.add_cog(Geral(bot))