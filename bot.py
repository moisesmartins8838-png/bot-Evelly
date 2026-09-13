import os
from pathlib import Path

import discord

from discord.ext import commands

from dotenv import load_dotenv

from database.database import criar_banco


# =========================================================
# CONFIGURAÇÃO
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)


DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")


if not DISCORD_TOKEN:
    raise RuntimeError(
        "❌ DISCORD_TOKEN não encontrado no .env"
    )


if not YOUTUBE_API_KEY:
    raise RuntimeError(
        "❌ YOUTUBE_API_KEY não encontrada no .env"
    )


# =========================================================
# INTENTS
# =========================================================

intents = discord.Intents.default()

intents.message_content = True
intents.members = True
intents.presences = True


# =========================================================
# BOT
# =========================================================

class Evelly(commands.Bot):

    def __init__(self):

        super().__init__(
            command_prefix="!",
            intents=intents
        )

        self.youtube_api_key = YOUTUBE_API_KEY


    # =====================================================
    # SETUP
    # =====================================================

    async def setup_hook(self):

        print("🔵 SETUP HOOK INICIADO", flush=True)

        print()
        print("=" * 60)
        print("🔵 SETUP HOOK INICIADO")
        print("=" * 60)
        print()


        # -------------------------------------------------
        # BANCO DE DADOS
        # -------------------------------------------------

        print("🔄 Inicializando banco de dados...")

        criar_banco()

        print("   ✅ Banco de dados pronto!")
        print()


        # -------------------------------------------------
        # COGS
        # -------------------------------------------------

        print("🔄 Carregando módulos...")
        print()


        # GERAL
        print("   🔄 Carregando geral...")

        await self.load_extension(
            "cogs.geral"
        )

        print("   ✅ geral")
        print()


        # CONFIGURAÇÃO
        print("   🔄 Carregando configuracao...")

        await self.load_extension(
            "cogs.configuracao"
        )

        print("   ✅ configuracao")
        print()


        # YOUTUBE
        print("   🔄 Carregando youtube...")

        await self.load_extension(
            "cogs.youtube"
        )

        print("   ✅ youtube")
        print()


        # -------------------------------------------------
        # SINCRONIZAÇÃO
        # -------------------------------------------------

        print("🔄 Sincronizando comandos...")

        synced = await self.tree.sync()

        print(
            f"✅ {len(synced)} comando(s) sincronizado(s)!"
        )

        print()

        for command in synced:

            print(
                f"   └─ /{command.name}"
            )

        print()


        # -------------------------------------------------
        # FINAL
        # -------------------------------------------------

        print("=" * 60)
        print("🟢 SETUP HOOK FINALIZADO")
        print("=" * 60)
        print()


# =========================================================
# INSTÂNCIA
# =========================================================

bot = Evelly()


# =========================================================
# EVENTO: BOT ONLINE
# =========================================================

@bot.event
async def on_ready():

    print()
    print("=" * 60)
    print("🤖 EVELLY ONLINE!")
    print("=" * 60)

    print(
        f"👤 Nome: {bot.user}"
    )

    print(
        f"🆔 ID: {bot.user.id}"
    )

    print(
        f"🌐 Servidores: {len(bot.guilds)}"
    )

    print(
        f"👥 Usuários conhecidos: {len(bot.users)}"
    )

    print(
        f"📡 Latência: "
        f"{round(bot.latency * 1000)}ms"
    )

    print(
        "🎬 YouTube: ATIVO"
    )

    print("=" * 60)
    print()


# =========================================================
# ERROS DOS SLASH COMMANDS
# =========================================================

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: discord.app_commands.AppCommandError
):

    print()
    print("=" * 60)
    print("❌ ERRO EM SLASH COMMAND")
    print("=" * 60)

    print(
        f"Comando: {interaction.command}"
    )

    print(
        f"Erro: {error}"
    )

    print()


    if not interaction.response.is_done():

        await interaction.response.send_message(
            "❌ Ocorreu um erro ao executar este comando.",
            ephemeral=True
        )


# =========================================================
# INICIAR BOT
# =========================================================

print()
print("🚀 Iniciando Evelly...")
print()

print("🟡 CHEGOU AO BOT.RUN()", flush=True)

bot.run(DISCORD_TOKEN)