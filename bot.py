import os
from pathlib import Path

import discord

from discord.ext import commands

from dotenv import load_dotenv

from database.database import criar_banco


# =========================================================
# CONFIGURAÇÕES
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)


DISCORD_TOKEN = os.getenv(
    "DISCORD_TOKEN"
)

YOUTUBE_API_KEY = os.getenv(
    "YOUTUBE_API_KEY"
)


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

    async def setup_hook(self):

        print()
        print("🔄 Inicializando banco de dados...")

        criar_banco()

        print(
            "   ✅ Banco de dados pronto!"
        )

        print()
        print("🔄 Carregando módulos...")

        await self.load_extension(
            "cogs.geral"
        )

        print(
            "   ✅ geral"
        )

        await self.load_extension(
            "cogs.configuracao"
        )

        print(
            "   ✅ configuracao"
        )

        await self.load_extension(
            "cogs.youtube"
        )

        print(
            "   ✅ youtube"
        )

        print()
        print(
            "🔄 Sincronizando comandos..."
        )

        synced = await self.tree.sync()

        print(
            f"✅ {len(synced)} comando(s) sincronizado(s)!"
        )

        for command in synced:

            print(
                f"   └─ /{command.name}"
            )

        print()


bot = Evelly()


# =========================================================
# BOT ONLINE
# =========================================================

@bot.event
async def on_ready():

    print()
    print(
        "=" * 60
    )

    print(
        "🤖 EVELLY ONLINE!"
    )

    print(
        "=" * 60
    )

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

    print(
        "=" * 60
    )

    print()


# =========================================================
# ERROS DE SLASH COMMAND
# =========================================================

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: discord.app_commands.AppCommandError
):

    print()
    print(
        "❌ ERRO EM SLASH COMMAND"
    )

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
# INICIAR
# =========================================================

bot.run(
    DISCORD_TOKEN
)