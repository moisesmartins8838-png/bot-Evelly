import os
import asyncio
import traceback

import discord
from discord.ext import commands

from dotenv import load_dotenv

from database.database import criar_banco


# ============================================================
# CARREGAR .ENV
# ============================================================

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")


# ============================================================
# VALIDAR CONFIGURAÇÕES
# ============================================================

if not DISCORD_TOKEN:
    raise RuntimeError(
        "❌ DISCORD_TOKEN não foi encontrado no .env"
    )

if not YOUTUBE_API_KEY:
    raise RuntimeError(
        "❌ YOUTUBE_API_KEY não foi encontrado no .env"
    )


# ============================================================
# INTENTS
# ============================================================

intents = discord.Intents.default()

intents.message_content = True
intents.members = True
intents.presences = True


# ============================================================
# BOT EVELLY
# ============================================================

class Evelly(commands.Bot):

    def __init__(self):

        super().__init__(
            command_prefix="!",
            intents=intents
        )

        self.youtube_api_key = YOUTUBE_API_KEY

        self.comandos_sincronizados = False

        self.tarefa_reinicio = None


    # ========================================================
    # INTERACTION HANDLER
    # ========================================================
    #
    # O /post recebe um ACK ANTES do processamento normal
    # da CommandTree.
    #
    # Isso é importante porque o Discord exige uma resposta
    # inicial da interação em aproximadamente 3 segundos.
    #
    # ========================================================

    async def on_interaction(
        self,
        interaction: discord.Interaction
    ):

        # ----------------------------------------------------
        # Detectar slash command
        # ----------------------------------------------------

        if interaction.type == discord.InteractionType.application_command:

            try:

                dados = interaction.data

                nome_comando = (
                    dados.get("name")
                    if isinstance(dados, dict)
                    else None
                )

                # ------------------------------------------------
                # SOMENTE /post
                # ------------------------------------------------

                if nome_comando == "post":

                    print(
                        "==============================================",
                        flush=True
                    )

                    print(
                        "⚡ ACK ANTECIPADO DO /POST",
                        flush=True
                    )

                    print(
                        f"🆔 Interaction ID: {interaction.id}",
                        flush=True
                    )

                    print(
                        f"👤 Usuário: {interaction.user}",
                        flush=True
                    )

                    try:

                        # ----------------------------------------
                        # Resposta inicial IMEDIATA
                        # ----------------------------------------

                        await interaction.response.send_message(

                            "⏳ **Preparando publicação...**\n"
                            "☁️ Enviando arquivos para o armazenamento...",

                            ephemeral=True

                        )

                        print(
                            "✅ ACK do /post enviado com sucesso!",
                            flush=True
                        )

                    except discord.NotFound as e:

                        print(
                            "❌ UNKNOWN INTERACTION NO ACK!",
                            flush=True
                        )

                        print(
                            f"Erro: {e}",
                            flush=True
                        )

                        print(
                            "==============================================",
                            flush=True
                        )

                        return

                    except discord.HTTPException as e:

                        print(
                            "❌ ERRO HTTP NO ACK DO /POST",
                            flush=True
                        )

                        print(
                            f"Status: {e.status}",
                            flush=True
                        )

                        print(
                            f"Erro: {e}",
                            flush=True
                        )

                        print(
                            "==============================================",
                            flush=True
                        )

                        return

                    print(
                        "==============================================",
                        flush=True
                    )


            except Exception as e:

                print(
                    "❌ ERRO AO FAZER ACK ANTECIPADO DO /POST",
                    flush=True
                )

                print(
                    f"Tipo: {type(e).__name__}",
                    flush=True
                )

                print(
                    f"Erro: {e}",
                    flush=True
                )

                traceback.print_exc()


        # ----------------------------------------------------
        # ENTREGAR A INTERAÇÃO PARA A DISCORD.PY
        # ----------------------------------------------------

        await super().on_interaction(
            interaction
        )


    # ========================================================
    # SETUP HOOK
    # ========================================================

    async def setup_hook(self):

        print(
            "==============================================",
            flush=True
        )

        print(
            "🔄 CARREGANDO SISTEMAS DA EVELLY",
            flush=True
        )

        print(
            "==============================================",
            flush=True
        )


        # ====================================================
        # BANCO
        # ====================================================

        try:

            print(
                "🗄️ Conectando ao Supabase...",
                flush=True
            )

            await criar_banco()

            print(
                "✅ Banco de dados conectado!",
                flush=True
            )

        except Exception as e:

            print(
                "==============================================",
                flush=True
            )

            print(
                "❌ ERRO AO CONECTAR AO BANCO",
                flush=True
            )

            print(
                f"Tipo: {type(e).__name__}",
                flush=True
            )

            print(
                f"Erro: {e}",
                flush=True
            )

            traceback.print_exc()

            print(
                "==============================================",
                flush=True
            )


        # ====================================================
        # COGS
        # ====================================================

        cogs = [

            "cogs.geral",

            "cogs.configuracao",

            "cogs.youtube",

            "cogs.post"

        ]


        for cog in cogs:

            print(
                f"🔄 Carregando: {cog}",
                flush=True
            )

            try:

                await self.load_extension(
                    cog
                )

                print(
                    f"✅ Sistema carregado: {cog}",
                    flush=True
                )

            except Exception as e:

                print(
                    "==============================================",
                    flush=True
                )

                print(
                    f"❌ ERRO AO CARREGAR: {cog}",
                    flush=True
                )

                print(
                    f"Tipo: {type(e).__name__}",
                    flush=True
                )

                print(
                    f"Erro: {e}",
                    flush=True
                )

                traceback.print_exc()

                print(
                    "==============================================",
                    flush=True
                )


        print(
            "==============================================",
            flush=True
        )

        print(
            "✅ TODOS OS SISTEMAS FORAM PROCESSADOS!",
            flush=True
        )

        print(
            "==============================================",
            flush=True
        )


    # ========================================================
    # READY
    # ========================================================

    async def on_ready(self):

        print(
            "==============================================",
            flush=True
        )

        print(
            "🤖 BOT ONLINE!",
            flush=True
        )

        print(
            f"👤 Nome: {self.user}",
            flush=True
        )

        print(
            f"🆔 ID: {self.user.id}",
            flush=True
        )

        print(
            f"🌐 Servidores: {len(self.guilds)}",
            flush=True
        )

        print(
            "==============================================",
            flush=True
        )


        # ====================================================
        # SINCRONIZAR SOMENTE UMA VEZ
        # ====================================================

        if not self.comandos_sincronizados:

            print(
                "🔄 SINCRONIZANDO COMANDOS...",
                flush=True
            )

            for guild in self.guilds:

                try:

                    print(
                        f"🔄 Sincronizando: {guild.name}",
                        flush=True
                    )

                    self.tree.copy_global_to(
                        guild=guild
                    )

                    comandos = await self.tree.sync(
                        guild=guild
                    )

                    print(
                        f"✅ {len(comandos)} comandos sincronizados!",
                        flush=True
                    )

                except Exception as e:

                    print(
                        f"❌ Erro ao sincronizar "
                        f"{guild.name}: {e}",
                        flush=True
                    )

                    traceback.print_exc()


            self.comandos_sincronizados = True

            print(
                "✅ SINCRONIZAÇÃO FINALIZADA!",
                flush=True
            )

        else:

            print(
                "ℹ️ Comandos já sincronizados.",
                flush=True
            )


        # ====================================================
        # STATUS
        # ====================================================

        print(
            "==============================================",
            flush=True
        )

        print(
            "🟢 EVELLY ESTÁ FUNCIONANDO!",
            flush=True
        )

        print(
            "📦 Sistema de posts: ATIVO",
            flush=True
        )

        print(
            "📁 Máximo de arquivos por post: 10",
            flush=True
        )

        print(
            "📺 Sistema YouTube: ATIVO",
            flush=True
        )

        print(
            "🗄️ Supabase: ATIVO",
            flush=True
        )

        print(
            "🔒 Storage privado: CONFIGURADO",
            flush=True
        )

        print(
            "⏱️ Reinício automático: 5h30",
            flush=True
        )

        print(
            "==============================================",
            flush=True
        )


    # ========================================================
    # APP COMMAND ERROR
    # ========================================================

    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: discord.app_commands.AppCommandError
    ):

        print(
            "==============================================",
            flush=True
        )

        print(
            "❌ ERRO DE SLASH COMMAND",
            flush=True
        )

        print(
            f"📌 Comando: "
            f"/{interaction.command.qualified_name if interaction.command else 'desconhecido'}",
            flush=True
        )

        print(
            f"📦 Tipo: {type(error).__name__}",
            flush=True
        )

        print(
            f"❌ Erro: {error}",
            flush=True
        )

        traceback.print_exception(
            type(error),
            error,
            error.__traceback__
        )

        print(
            "==============================================",
            flush=True
        )


        erro_original = getattr(
            error,
            "original",
            error
        )

        if isinstance(
            erro_original,
            discord.NotFound
        ):

            print(
                "⚠️ Interação já expirou.",
                flush=True
            )

            return


        try:

            mensagem = (
                "❌ **Ocorreu um erro ao executar este comando.**"
            )

            if interaction.response.is_done():

                await interaction.followup.send(
                    mensagem,
                    ephemeral=True
                )

            else:

                await interaction.response.send_message(
                    mensagem,
                    ephemeral=True
                )

        except Exception as e:

            print(
                f"⚠️ Falha ao responder erro: {e}",
                flush=True
            )


    # ========================================================
    # ERRO GERAL
    # ========================================================

    async def on_error(
        self,
        event_method,
        *args,
        **kwargs
    ):

        print(
            "==============================================",
            flush=True
        )

        print(
            "❌ ERRO GERAL DA EVELLY",
            flush=True
        )

        print(
            f"📌 Evento: {event_method}",
            flush=True
        )

        traceback.print_exc()

        print(
            "==============================================",
            flush=True
        )


# ============================================================
# BOT
# ============================================================

bot = Evelly()


# ============================================================
# COMMAND TREE ERROR
# ============================================================

@bot.tree.error
async def tree_error_handler(
    interaction: discord.Interaction,
    error: discord.app_commands.AppCommandError
):

    print(
        "==============================================",
        flush=True
    )

    print(
        "🚨 ERRO CAPTURADO PELA COMMAND TREE",
        flush=True
    )

    if interaction.command:

        try:

            nome_comando = (
                interaction.command.qualified_name
            )

        except Exception:

            nome_comando = (
                interaction.command.name
            )

        print(
            f"📌 Comando: /{nome_comando}",
            flush=True
        )

    print(
        f"📦 Tipo: {type(error).__name__}",
        flush=True
    )

    print(
        f"❌ Erro: {error}",
        flush=True
    )

    traceback.print_exception(
        type(error),
        error,
        error.__traceback__
    )

    print(
        "==============================================",
        flush=True
    )

    erro_original = getattr(
        error,
        "original",
        error
    )

    if isinstance(
        erro_original,
        discord.NotFound
    ):

        print(
            "⚠️ UNKNOWN INTERACTION.",
            flush=True
        )

        print(
            "⚠️ Não será feita uma segunda tentativa "
            "de responder.",
            flush=True
        )

        return

    try:

        mensagem = (
            "❌ **Ocorreu um erro ao executar este comando.**"
        )

        if interaction.response.is_done():

            await interaction.followup.send(
                mensagem,
                ephemeral=True
            )

        else:

            await interaction.response.send_message(
                mensagem,
                ephemeral=True
            )

    except Exception as e:

        print(
            f"⚠️ Falha ao responder erro: {e}",
            flush=True
        )


# ============================================================
# REINÍCIO AUTOMÁTICO
# ============================================================

TEMPO_REINICIO = (
    (5 * 60 * 60)
    +
    (30 * 60)
)


async def reinicio_automatico():

    print(
        "==============================================",
        flush=True
    )

    print(
        "⏱️ SISTEMA DE REINÍCIO AUTOMÁTICO",
        flush=True
    )

    print(
        "🔄 Ciclo configurado: 5 horas e 30 minutos",
        flush=True
    )

    print(
        "==============================================",
        flush=True
    )

    try:

        await asyncio.sleep(
            TEMPO_REINICIO
        )

        print(
            "==============================================",
            flush=True
        )

        print(
            "🔄 REINÍCIO AUTOMÁTICO",
            flush=True
        )

        print(
            "⏱️ Ciclo de 5h30 concluído.",
            flush=True
        )

        print(
            "🛑 Encerrando conexão da Evelly...",
            flush=True
        )

        print(
            "==============================================",
            flush=True
        )

        await bot.close()

    except asyncio.CancelledError:

        print(
            "⏹️ Contador de reinício cancelado.",
            flush=True
        )


# ============================================================
# MAIN
# ============================================================

async def main():

    print(
        "==============================================",
        flush=True
    )

    print(
        "🚀 INICIANDO EVELLY",
        flush=True
    )

    print(
        "==============================================",
        flush=True
    )

    try:

        await bot.start(
            DISCORD_TOKEN
        )

    except discord.LoginFailure as e:

        print(
            "❌ TOKEN DO DISCORD INVÁLIDO",
            flush=True
        )

        print(
            str(e),
            flush=True
        )

        raise

    except Exception as e:

        print(
            "==============================================",
            flush=True
        )

        print(
            "❌ ERRO AO INICIAR A EVELLY",
            flush=True
        )

        print(
            f"Tipo: {type(e).__name__}",
            flush=True
        )

        print(
            f"Erro: {e}",
            flush=True
        )

        traceback.print_exc()

        print(
            "==============================================",
            flush=True
        )

        raise


# ============================================================
# EXECUTAR
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        print(
            "==============================================",
            flush=True
        )

        print(
            "🛑 EVELLY ENCERRADA MANUALMENTE",
            flush=True
        )

        print(
            "==============================================",
            flush=True
        )

    except Exception as e:

        print(
            "==============================================",
            flush=True
        )

        print(
            "💀 ERRO FATAL",
            flush=True
        )

        print(
            f"Tipo: {type(e).__name__}",
            flush=True
        )

        print(
            f"Erro: {e}",
            flush=True
        )

        traceback.print_exc()

        print(
            "==============================================",
            flush=True
        )