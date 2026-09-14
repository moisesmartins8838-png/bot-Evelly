import os
import asyncio
import traceback
import time

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

        # Monitor do Event Loop
        self._monitor_event_loop = None


    # ========================================================
    # CARREGAR SISTEMAS
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
        # BANCO DE DADOS
        # ====================================================

        try:

            print(
                "🗄️ Conectando ao Supabase...",
                flush=True
            )

            await asyncio.to_thread(
                criar_banco
            )

            print(
                "☁️ Banco Supabase conectado!",
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
        #
        # TESTE DE ISOLAMENTO
        #
        # SOMENTE O COG "GERAL" ESTÁ ATIVO.
        #
        # NÃO CARREGAR:
        # cogs.configuracao
        # cogs.post
        # cogs.musica
        # cogs.youtube
        #
        # ====================================================

        cogs = [
            "cogs.geral"
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
            "✅ TESTE DE ISOLAMENTO CONFIGURADO!",
            flush=True
        )

        print(
            "📦 Cogs ativos: cogs.geral",
            flush=True
        )

        print(
            "🚫 Configuração: DESATIVADA",
            flush=True
        )

        print(
            "🚫 Posts: DESATIVADO",
            flush=True
        )

        print(
            "🚫 Música: DESATIVADO",
            flush=True
        )

        print(
            "🚫 YouTube: DESATIVADO",
            flush=True
        )

        print(
            "==============================================",
            flush=True
        )


    # ========================================================
    # BOT ONLINE
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
        # SINCRONIZAR SLASH COMMANDS
        # ====================================================

        for guild in self.guilds:

            try:

                print(
                    f"🔄 Sincronizando comandos: {guild.name}",
                    flush=True
                )

                self.tree.copy_global_to(
                    guild=guild
                )

                comandos = await self.tree.sync(
                    guild=guild
                )

                print(
                    "✅ Comandos sincronizados!",
                    flush=True
                )

                print(
                    f"📋 Total: {len(comandos)}",
                    flush=True
                )

                for comando in comandos:

                    try:
                        nome = comando.qualified_name

                    except Exception:
                        nome = comando.name

                    print(
                        f"   └─ /{nome}",
                        flush=True
                    )

            except Exception as e:

                print(
                    "==============================================",
                    flush=True
                )

                print(
                    f"❌ ERRO AO SINCRONIZAR {guild.name}",
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
        # INICIAR MONITOR DO EVENT LOOP
        # ====================================================

        if (
            self._monitor_event_loop is None
            or self._monitor_event_loop.done()
        ):

            self._monitor_event_loop = asyncio.create_task(
                self.monitorar_event_loop()
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
            "🧪 MODO DE TESTE DE ISOLAMENTO",
            flush=True
        )

        print(
            "----------------------------------------------",
            flush=True
        )

        print(
            "✅ Sistema Geral: ATIVO",
            flush=True
        )

        print(
            "🚫 Sistema de configuração: DESATIVADO",
            flush=True
        )

        print(
            "🚫 Sistema de posts: DESATIVADO",
            flush=True
        )

        print(
            "🚫 Sistema de música: DESATIVADO",
            flush=True
        )

        print(
            "🚫 Sistema YouTube: DESATIVADO",
            flush=True
        )

        print(
            "----------------------------------------------",
            flush=True
        )

        print(
            "🔎 Monitor do Event Loop: ATIVO",
            flush=True
        )

        print(
            "==============================================",
            flush=True
        )


    # ========================================================
    # MONITOR DO EVENT LOOP
    # ========================================================

    async def monitorar_event_loop(self):

        print(
            "🔎 Monitor do Event Loop iniciado!",
            flush=True
        )

        while not self.is_closed():

            inicio = time.monotonic()

            await asyncio.sleep(1)

            atraso = (
                time.monotonic()
                - inicio
                - 1
            )


            if atraso > 0.5:

                print(
                    "==============================================",
                    flush=True
                )

                print(
                    "⚠️ [EVENT LOOP] BLOQUEIO DETECTADO",
                    flush=True
                )

                print(
                    f"⏱️ Atraso: {atraso:.2f}s",
                    flush=True
                )

                print(
                    "==============================================",
                    flush=True
                )


    # ========================================================
    # ERRO DOS SLASH COMMANDS
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
            f"👤 Usuário: {interaction.user}",
            flush=True
        )

        print(
            f"🆔 User ID: {interaction.user.id}",
            flush=True
        )

        print(
            f"🌐 Servidor: "
            f"{interaction.guild.name if interaction.guild else 'DM'}",
            flush=True
        )

        try:

            nome_comando = (
                interaction.command.qualified_name
                if interaction.command
                else "desconhecido"
            )

        except Exception:

            nome_comando = "desconhecido"


        print(
            f"📌 Comando: /{nome_comando}",
            flush=True
        )

        print(
            f"📦 Tipo do erro: {type(error).__name__}",
            flush=True
        )

        print(
            f"❌ Erro: {error}",
            flush=True
        )


        # ====================================================
        # ERRO ORIGINAL
        # ====================================================

        original = getattr(
            error,
            "original",
            error
        )

        print(
            "----------------------------------------------",
            flush=True
        )

        print(
            "🔎 ERRO ORIGINAL",
            flush=True
        )

        print(
            f"Tipo: {type(original).__name__}",
            flush=True
        )

        print(
            f"Erro: {original}",
            flush=True
        )


        # ====================================================
        # TRACEBACK
        # ====================================================

        print(
            "----------------------------------------------",
            flush=True
        )

        print(
            "📜 TRACEBACK COMPLETO",
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


        # ====================================================
        # INTERAÇÃO EXPIRADA
        # ====================================================
        #
        # 10062 = Unknown Interaction
        #
        # Se a interação já expirou, NÃO tentar responder.
        # Isso evita o segundo erro 40060.
        # ====================================================

        if isinstance(
            original,
            discord.NotFound
        ):

            print(
                "⏰ A interação já expirou.",
                flush=True
            )

            print(
                "🚫 Nenhuma resposta será enviada ao Discord.",
                flush=True
            )

            return


        # ====================================================
        # RESPONDER NO DISCORD
        # ====================================================

        try:

            mensagem = (
                "❌ **Ocorreu um erro ao executar este comando.**\n\n"
                "🔎 Verifique o terminal da Evelly "
                "para ver o erro real."
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


        except discord.NotFound:

            print(
                "⏰ A interação expirou antes da resposta.",
                flush=True
            )

        except discord.HTTPException as e:

            print(
                "⚠️ Discord recusou a resposta de erro.",
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

        except Exception as e:

            print(
                "⚠️ Não foi possível enviar "
                "a mensagem de erro no Discord.",
                flush=True
            )

            print(
                f"Erro: {e}",
                flush=True
            )


    # ========================================================
    # ERROS GERAIS
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
# CRIAR BOT
# ============================================================

bot = Evelly()


# ============================================================
# TRATAMENTO DIRETO DA COMMAND TREE
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


    # ========================================================
    # NOME DO COMANDO
    # ========================================================

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


    # ========================================================
    # ERRO ORIGINAL
    # ========================================================

    original = getattr(
        error,
        "original",
        error
    )

    print(
        "----------------------------------------------",
        flush=True
    )

    print(
        "🔎 ERRO ORIGINAL:",
        flush=True
    )

    print(
        repr(original),
        flush=True
    )


    # ========================================================
    # TRACEBACK
    # ========================================================

    print(
        "----------------------------------------------",
        flush=True
    )

    print(
        "📜 TRACEBACK COMPLETO:",
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


    # ========================================================
    # NÃO TENTAR RESPONDER SE A INTERAÇÃO EXPIROU
    # ========================================================

    if isinstance(
        original,
        discord.NotFound
    ):

        print(
            "⏰ Interaction 10062 detectada.",
            flush=True
        )

        print(
            "🚫 Resposta de erro cancelada.",
            flush=True
        )

        return


    # ========================================================
    # MENSAGEM DE ERRO
    # ========================================================

    try:

        mensagem = (
            "❌ **Ocorreu um erro ao executar este comando.**\n\n"
            "🔎 Verifique o terminal da Evelly "
            "para ver o erro real."
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


    except discord.NotFound:

        print(
            "⏰ A interação expirou antes da resposta.",
            flush=True
        )

    except discord.HTTPException as e:

        print(
            "⚠️ Falha HTTP ao responder o erro:",
            flush=True
        )

        print(
            repr(e),
            flush=True
        )

    except Exception as e:

        print(
            "⚠️ Falha ao responder o erro no Discord:",
            flush=True
        )

        print(
            repr(e),
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
            "📡 GitHub Actions deverá iniciar "
            "o próximo ciclo.",
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
        "🧪 MODO DE TESTE: SOMENTE COGS.GERAL",
        flush=True
    )

    print(
        "==============================================",
        flush=True
    )


    tarefa_reinicio = asyncio.create_task(
        reinicio_automatico()
    )


    try:

        await bot.start(
            DISCORD_TOKEN
        )


    except discord.LoginFailure as e:

        print(
            "==============================================",
            flush=True
        )

        print(
            "❌ TOKEN DO DISCORD INVÁLIDO",
            flush=True
        )

        print(
            str(e),
            flush=True
        )

        print(
            "==============================================",
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


    finally:

        if not tarefa_reinicio.done():

            tarefa_reinicio.cancel()

            try:

                await tarefa_reinicio

            except asyncio.CancelledError:

                pass


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