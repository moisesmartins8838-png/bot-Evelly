# ============================================================
# EVELLY • LIMPAR
# ============================================================
#
# Comando:
# /limpar quantidade:50
#
# Apaga de 1 até 100 mensagens do canal atual.
#
# ============================================================

import discord
from discord import app_commands
from discord.ext import commands


# ============================================================
# COG
# ============================================================

class LimparCog(commands.Cog):

    def __init__(self, bot: commands.Bot):

        self.bot = bot

        print(
            "🧹 Sistema /limpar carregado com sucesso.",
            flush=True
        )


    # ========================================================
    # /LIMPAR
    # ========================================================

    @app_commands.command(
        name="limpar",
        description="Apaga de 1 até 100 mensagens deste canal."
    )
    @app_commands.describe(
        quantidade="Quantidade de mensagens para apagar (1 a 100)."
    )
    @app_commands.checks.has_permissions(
        manage_messages=True
    )
    async def limpar(
        self,
        interaction: discord.Interaction,
        quantidade: app_commands.Range[int, 1, 100]
    ):

        # ====================================================
        # VERIFICAR SERVIDOR
        # ====================================================

        if interaction.guild is None:

            await interaction.response.send_message(
                "❌ Este comando só pode ser usado dentro de um servidor.",
                ephemeral=True
            )

            return


        # ====================================================
        # VERIFICAR CANAL
        # ====================================================

        if not isinstance(
            interaction.channel,
            discord.TextChannel
        ):

            await interaction.response.send_message(
                "❌ Este comando só pode ser usado em canais de texto.",
                ephemeral=True
            )

            return


        # ====================================================
        # VERIFICAR PERMISSÃO DA EVELLY
        # ====================================================

        bot_member = interaction.guild.me

        if bot_member is None:

            await interaction.response.send_message(
                "❌ Não consegui verificar minhas permissões.",
                ephemeral=True
            )

            return


        permissoes = interaction.channel.permissions_for(
            bot_member
        )


        if not permissoes.manage_messages:

            await interaction.response.send_message(
                (
                    "❌ Eu não tenho a permissão "
                    "**Gerenciar Mensagens** neste canal."
                ),
                ephemeral=True
            )

            return


        # ====================================================
        # AVISO
        # ====================================================

        await interaction.response.defer(
            ephemeral=True
        )


        # ====================================================
        # APAGAR MENSAGENS
        # ====================================================

        try:

            apagadas = await interaction.channel.purge(
                limit=int(quantidade)
            )


        except discord.Forbidden:

            await interaction.followup.send(
                (
                    "❌ Não tenho permissão para apagar "
                    "mensagens neste canal."
                ),
                ephemeral=True
            )

            return


        except discord.HTTPException as erro:

            print(
                "❌ [LIMPAR] Erro HTTP:",
                erro,
                flush=True
            )

            await interaction.followup.send(
                (
                    "❌ O Discord recusou a operação. "
                    "Tente novamente em alguns segundos."
                ),
                ephemeral=True
            )

            return


        except Exception as erro:

            print(
                "❌ [LIMPAR] Erro inesperado:",
                erro,
                flush=True
            )

            await interaction.followup.send(
                "❌ Ocorreu um erro ao limpar o canal.",
                ephemeral=True
            )

            return


        # ====================================================
        # RESULTADO
        # ====================================================

        quantidade_apagada = len(
            apagadas
        )


        await interaction.followup.send(
            (
                "🧹 **Limpeza concluída!**\n\n"
                f"🗑️ Mensagens apagadas: **{quantidade_apagada}**\n"
                f"👤 Executado por: {interaction.user.mention}"
            ),
            ephemeral=True
        )


        # ====================================================
        # LOG
        # ====================================================

        print(
            "==============================================",
            flush=True
        )

        print(
            "🧹 EVELLY • LIMPAR",
            flush=True
        )

        print(
            f"👤 Executor: {interaction.user}",
            flush=True
        )

        print(
            f"🆔 Executor ID: {interaction.user.id}",
            flush=True
        )

        print(
            f"🏠 Servidor: {interaction.guild.name}",
            flush=True
        )

        print(
            f"🆔 Guild ID: {interaction.guild.id}",
            flush=True
        )

        print(
            f"💬 Canal: #{interaction.channel.name}",
            flush=True
        )

        print(
            f"🆔 Canal ID: {interaction.channel.id}",
            flush=True
        )

        print(
            f"📥 Solicitadas: {quantidade}",
            flush=True
        )

        print(
            f"🗑️ Apagadas: {quantidade_apagada}",
            flush=True
        )

        print(
            "✅ Limpeza concluída.",
            flush=True
        )

        print(
            "==============================================",
            flush=True
        )


    # ========================================================
    # TRATAMENTO DE PERMISSÃO
    # ========================================================

    @limpar.error
    async def limpar_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError
    ):

        if isinstance(
            error,
            app_commands.MissingPermissions
        ):

            mensagem = (
                "❌ Você precisa da permissão "
                "**Gerenciar Mensagens** para usar este comando."
            )

        else:

            print(
                f"❌ [LIMPAR] Erro no comando: {error}",
                flush=True
            )

            mensagem = (
                "❌ Não foi possível executar o comando."
            )


        try:

            if not interaction.response.is_done():

                await interaction.response.send_message(
                    mensagem,
                    ephemeral=True
                )

            else:

                await interaction.followup.send(
                    mensagem,
                    ephemeral=True
                )

        except Exception as erro:

            print(
                f"⚠️ [LIMPAR] Erro ao enviar resposta: {erro}",
                flush=True
            )


# ============================================================
# SETUP
# ============================================================

async def setup(
    bot: commands.Bot
):

    await bot.add_cog(
        LimparCog(bot)
    )

    print(
        "🧹 cogs.limpar carregado com sucesso.",
        flush=True
    )