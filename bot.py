import os
import asyncio

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
        "❌ DISCORD_TOKEN não foi encontrado no arquivo .env"
    )

if not YOUTUBE_API_KEY:
    raise RuntimeError(
        "❌ YOUTUBE_API_KEY não foi encontrado no arquivo .env"
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

    # --------------------------------------------------------
    # CARREGAR COGS
    # --------------------------------------------------------

    async def setup_hook(self):

        print("🔄 Carregando sistemas da Evelly...", flush=True)

        # Banco de dados
        try:
            await criar_banco()
            print("🗄️ Banco de dados conectado!", flush=True)

        except Exception as e:
            print(
                f"⚠️ Erro ao conectar ao banco: {e}",
                flush=True
            )

        # ----------------------------------------------------
        # COGS
        # ----------------------------------------------------

        cogs = [
            "cogs.geral",
            "cogs.configuracao",
            "cogs.youtube",
        ]

        for cog in cogs:

            try:

                await self.load_extension(cog)

                print(
                    f"✅ Sistema carregado: {cog}",
                    flush=True
                )

            except Exception as e:

                print(
                    f"❌ Erro ao carregar {cog}: {e}",
                    flush=True
                )

        print(
            "✅ Todos os sistemas foram carregados!",
            flush=True
        )

    # --------------------------------------------------------
    # BOT ONLINE
    # --------------------------------------------------------

    async def on_ready(self):

        print(
            "==============================================",
            flush=True
        )

        print(
            f"🤖 BOT ONLINE: {self.user}",
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

        # ----------------------------------------------------
        # SINCRONIZAR SLASH COMMANDS
        # ----------------------------------------------------

        for guild in self.guilds:

            try:

                self.tree.copy_global_to(
                    guild=guild
                )

                comandos = await self.tree.sync(
                    guild=guild
                )

                print(
                    f"🔄 Comandos sincronizados em: "
                    f"{guild.name}",
                    flush=True
                )

                print(
                    f"📋 Total sincronizado: "
                    f"{len(comandos)} comando(s)",
                    flush=True
                )

                for comando in comandos:

                    print(
                        f"   └─ /{comando.name}",
                        flush=True
                    )

            except Exception as e:

                print(
                    f"❌ Erro ao sincronizar "
                    f"{guild.name}: {e}",
                    flush=True
                )

        print(
            "==============================================",
            flush=True
        )

        print(
            "🟢 EVELLY ESTÁ FUNCIONANDO!",
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

    # --------------------------------------------------------
    # ERROS DOS SLASH COMMANDS
    # --------------------------------------------------------

    async def on_tree_error(
        self,
        interaction: discord.Interaction,
        error: discord.app_commands.AppCommandError
    ):

        print(
            f"❌ Erro em comando: {error}",
            flush=True
        )

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

        except Exception:

            pass


# ============================================================
# CRIAR BOT
# ============================================================

bot = Evelly()


# ============================================================
# REINÍCIO AUTOMÁTICO
# ============================================================

# 5 horas e 30 minutos
TEMPO_REINICIO = (
    5 * 60 * 60
    +
    30 * 60
)


async def reinicio_automatico():

    print(
        "⏱️ Sistema de reinício automático iniciado.",
        flush=True
    )

    print(
        "🔄 A Evelly será encerrada em 5h30.",
        flush=True
    )

    await asyncio.sleep(TEMPO_REINICIO)

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
        "🛑 Encerrando a Evelly...",
        flush=True
    )

    print(
        "📡 O GitHub Actions iniciará o próximo ciclo.",
        flush=True
    )

    print(
        "==============================================",
        flush=True
    )

    await bot.close()


# ============================================================
# INICIALIZAÇÃO
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

    # Iniciar contador de reinício
    asyncio.create_task(
        reinicio_automatico()
    )

    # Iniciar Discord
    await bot.start(
        DISCORD_TOKEN
    )


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
            "🛑 Evelly encerrada manualmente.",
            flush=True
        )

    except Exception as e:

        print(
            f"❌ Erro fatal: {e}",
            flush=True
        )