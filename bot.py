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

            criar_banco()

            print(
                "☁️ Banco Supabase conectado!",
                flush=True
            )

        except Exception as erro:

            print(
                "==============================================",
                flush=True
            )

            print(
                "❌ ERRO AO CONECTAR AO BANCO",
                flush=True
            )

            print(
                f"Tipo: {type(erro).__name__}",
                flush=True
            )

            print(
                f"Erro: {erro}",
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
            "cogs.post",
            "cogs.call",
            "cogs.enviarpv",
            "cogs.linknot",
            "cogs.welcome",
            "cogs.callauto",
            "cogs.permissoes",
            "cogs.automsg",
        ]


        # ====================================================
        # CARREGAR COGS
        # ====================================================

        for cog in cogs:

            print(
                f"🔄 Carregando: {cog}",
                flush=True
            )

            try:

                await self.load_extension(cog)

                print(
                    f"✅ Sistema carregado: {cog}",
                    flush=True
                )

            except Exception as erro:

                print(
                    "==============================================",
                    flush=True
                )

                print(
                    f"❌ ERRO AO CARREGAR: {cog}",
                    flush=True
                )

                print(
                    f"Tipo: {type(erro).__name__}",
                    flush=True
                )

                print(
                    f"Erro: {erro}",
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
    # PRESENÇA / STATUS DO DISCORD
    # ========================================================

    async def atualizar_presenca(self):

        try:

            atividade = discord.Game(
                name="Com ela <3"
            )

            await self.change_presence(
                status=discord.Status.online,
                activity=atividade
            )

            print(
                "💜 Rich Presence da Evelly atualizado!",
                flush=True
            )

            print(
                "   └─ Jogando: Com ela <3",
                flush=True
            )

        except Exception as erro:

            print(
                f"⚠️ Erro ao atualizar presença: {erro}",
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
        # PRESENÇA
        # ====================================================

        await self.atualizar_presenca()


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

            except Exception as erro:

                print(
                    "==============================================",
                    flush=True
                )

                print(
                    f"❌ ERRO AO SINCRONIZAR {guild.name}",
                    flush=True
                )

                print(
                    f"Tipo: {type(erro).__name__}",
                    flush=True
                )

                print(
                    f"Erro: {erro}",
                    flush=True
                )

                traceback.print_exc()

                print(
                    "==============================================",
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
            "📺 Sistema YouTube: ATIVO",
            flush=True
        )

        print(
            "📞 Sistema de call: ATIVO",
            flush=True
        )

        print(
            "📨 Sistema EnviarPV: ATIVO",
            flush=True
        )

        print(
            "🔗 Sistema LinkNot: ATIVO",
            flush=True
        )

        print(
            "💜 Sistema de boas-vindas: ATIVO",
            flush=True
        )

        print(
            "🔇 Sistema de música: REMOVIDO",
            flush=True
        )

        print(
            "💜 Presença Discord: ATIVA",
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


        # ====================================================
        # DESCONECTAR DE CALLS
        # ====================================================

        for guild in bot.guilds:

            voice = guild.voice_client

            if voice:

                try:

                    await voice.disconnect(
                        force=True
                    )

                except Exception as erro:

                    print(
                        f"[CALL] Erro ao desconectar "
                        f"{guild.name}: {erro}",
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


    tarefa_reinicio = asyncio.create_task(
        reinicio_automatico()
    )


    try:

        await bot.start(
            DISCORD_TOKEN
        )


    except discord.LoginFailure as erro:

        print(
            "==============================================",
            flush=True
        )

        print(
            "❌ TOKEN DO DISCORD INVÁLIDO",
            flush=True
        )

        print(
            str(erro),
            flush=True
        )

        print(
            "==============================================",
            flush=True
        )

        raise


    except Exception as erro:

        print(
            "==============================================",
            flush=True
        )

        print(
            "❌ ERRO AO INICIAR A EVELLY",
            flush=True
        )

        print(
            f"Tipo: {type(erro).__name__}",
            flush=True
        )

        print(
            f"Erro: {erro}",
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

    except Exception as erro:

        print(
            "==============================================",
            flush=True
        )

        print(
            "💀 ERRO FATAL",
            flush=True
        )

        print(
            f"Tipo: {type(erro).__name__}",
            flush=True
        )

        print(
            f"Erro: {erro}",
            flush=True
        )

        traceback.print_exc()

        print(
            "==============================================",
            flush=True
        )