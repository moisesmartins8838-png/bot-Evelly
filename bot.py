import os
import asyncio
import traceback
import time

import discord
from discord.ext import commands
from dotenv import load_dotenv

from database.database import criar_banco


# ============================================================
# CONFIGURAÇÃO
# ============================================================

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN não encontrado no arquivo .env")


# ============================================================
# BOT
# ============================================================

class Evelly(commands.Bot):

    def __init__(self):
        intents = discord.Intents.default()

        intents.guilds = True
        intents.members = True
        intents.message_content = True
        intents.voice_states = True

        super().__init__(
            command_prefix="!",
            intents=intents
        )

        self.inicio = time.time()
        self.monitor_iniciado = False


    # ========================================================
    # SETUP HOOK
    # ========================================================

    async def setup_hook(self):

        print("==============================================")
        print("🔄 CARREGANDO SISTEMAS DA EVELLY")
        print("==============================================")

        # ----------------------------------------------------
        # BANCO DE DADOS
        # ----------------------------------------------------

        try:
            print("🗄️ Conectando ao Supabase...")

            await asyncio.to_thread(criar_banco)

            print("☁️ Banco Supabase conectado!")

        except Exception as e:
            print("❌ Erro ao conectar ao banco:")
            print(repr(e))

            traceback.print_exc()


        # ----------------------------------------------------
        # COGS
        # ----------------------------------------------------

        # MODO DE TESTE:
        # Geral + Música
        #
        # Os outros sistemas permanecem desligados
        # para conseguirmos identificar qualquer problema.

        cogs = [
            "cogs.geral",
            "cogs.musica",
        ]

        for cog in cogs:

            try:

                print(f"🔄 Carregando: {cog}")

                await self.load_extension(cog)

                print(f"✅ Sistema carregado: {cog}")

            except Exception as e:

                print(f"❌ ERRO ao carregar {cog}")
                print(f"❌ {type(e).__name__}: {e}")

                traceback.print_exc()


        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        print("==============================================")
        print("🧪 MODO DE TESTE")
        print("📦 Cogs ativos:")
        print("   ├─ cogs.geral")
        print("   └─ cogs.musica")
        print("----------------------------------------------")
        print("🚫 Configuração: DESATIVADA")
        print("🚫 Posts: DESATIVADO")
        print("🚫 YouTube: DESATIVADO")
        print("==============================================")


    # ========================================================
    # MONITOR DO EVENT LOOP
    # ========================================================

    async def monitorar_event_loop(self):

        print("==============================================")
        print("🔎 Monitor do Event Loop iniciado!")
        print("==============================================")

        ultimo = time.monotonic()

        while not self.is_closed():

            await asyncio.sleep(1)

            agora = time.monotonic()

            atraso = agora - ultimo - 1

            if atraso > 0.5:

                print(
                    f"⚠️ [EVENT LOOP] POSSÍVEL BLOQUEIO: "
                    f"{atraso:.3f}s"
                )

            ultimo = agora


    # ========================================================
    # BOT ONLINE
    # ========================================================

    async def on_ready(self):

        print("==============================================")
        print("🤖 BOT ONLINE!")
        print(f"👤 Nome: {self.user}")
        print(f"🆔 ID: {self.user.id}")
        print(f"🌐 Servidores: {len(self.guilds)}")
        print("==============================================")


        # ----------------------------------------------------
        # SINCRONIZAÇÃO DOS COMANDOS
        # ----------------------------------------------------

        for guild in self.guilds:

            try:

                print(
                    f"🔄 Sincronizando comandos: "
                    f"{guild.name}"
                )

                self.tree.copy_global_to(guild=guild)

                comandos = await self.tree.sync(
                    guild=guild
                )

                print("✅ Comandos sincronizados!")
                print(f"📋 Total: {len(comandos)}")

                for comando in comandos:

                    print(
                        f"   └─ /{comando.name}"
                    )

            except Exception as e:

                print(
                    f"❌ Erro ao sincronizar "
                    f"{guild.name}: {e}"
                )

                traceback.print_exc()


        # ----------------------------------------------------
        # STATUS FINAL
        # ----------------------------------------------------

        print("==============================================")
        print("🟢 EVELLY ESTÁ FUNCIONANDO!")
        print("🧪 MODO DE TESTE")
        print("----------------------------------------------")
        print("✅ Sistema Geral: ATIVO")
        print("✅ Sistema de música: ATIVO")
        print("🚫 Sistema de configuração: DESATIVADO")
        print("🚫 Sistema de posts: DESATIVADO")
        print("🚫 Sistema YouTube: DESATIVADO")
        print("----------------------------------------------")
        print("🔎 Monitor do Event Loop: ATIVO")
        print("==============================================")


        # ----------------------------------------------------
        # MONITOR
        # ----------------------------------------------------

        if not self.monitor_iniciado:

            self.monitor_iniciado = True

            asyncio.create_task(
                self.monitorar_event_loop()
            )


    # ========================================================
    # ERRO DOS COMANDOS
    # ========================================================

    async def on_command_error(self, ctx, error):

        print("==============================================")
        print("❌ ERRO DE COMANDO")
        print(f"Comando: {getattr(ctx.command, 'name', 'desconhecido')}")
        print(f"Tipo: {type(error).__name__}")
        print(f"Erro: {error}")
        print("==============================================")

        traceback.print_exception(
            type(error),
            error,
            error.__traceback__
        )


# ============================================================
# CRIAÇÃO DO BOT
# ============================================================

bot = Evelly()


# ============================================================
# ERROS DE INTERAÇÃO
# ============================================================

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error
):

    print("==============================================")
    print("❌ ERRO DE SLASH COMMAND")
    print(f"Tipo: {type(error).__name__}")
    print(f"Erro: {error}")
    print("==============================================")


    # --------------------------------------------------------
    # INTERAÇÃO EXPIRADA
    # --------------------------------------------------------

    if isinstance(error, discord.NotFound):

        print("⏰ Interaction 10062 detectada.")
        print("🚫 Resposta de erro cancelada.")

        return


    # --------------------------------------------------------
    # ERRO NORMAL
    # --------------------------------------------------------

    try:

        if interaction.response.is_done():

            await interaction.followup.send(
                "❌ Ocorreu um erro ao executar o comando.",
                ephemeral=True
            )

        else:

            await interaction.response.send_message(
                "❌ Ocorreu um erro ao executar o comando.",
                ephemeral=True
            )

    except Exception as e:

        print(
            f"❌ Não foi possível enviar "
            f"a mensagem de erro: {e}"
        )


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":

    print("==============================================")
    print("🚀 INICIANDO EVELLY")
    print("==============================================")
    print("⏱️ Tempo máximo deste ciclo: 5h50")
    print("🔄 Após o ciclo, uma nova execução será criada.")
    print("==============================================")


    async def reinicio_automatico():

        await asyncio.sleep(
            5 * 60 * 60 + 30 * 60
        )

        print("==============================================")
        print("🔄 TEMPO DE EXECUÇÃO ENCERRADO")
        print("🔄 Encerrando bot...")
        print("==============================================")


        await bot.close()


    async def iniciar():

        tarefa_reinicio = asyncio.create_task(
            reinicio_automatico()
        )

        try:

            await bot.start(TOKEN)

        finally:

            tarefa_reinicio.cancel()


    try:

        asyncio.run(iniciar())

    except KeyboardInterrupt:

        print("🛑 Evelly encerrada manualmente.")

    except Exception as e:

        print("==============================================")
        print("❌ ERRO FATAL")
        print(f"{type(e).__name__}: {e}")
        print("==============================================")

        traceback.print_exc()