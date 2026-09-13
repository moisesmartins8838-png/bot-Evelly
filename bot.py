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
        "❌ DISCORD_TOKEN não encontrado."
    )


if not YOUTUBE_API_KEY:
    raise RuntimeError(
        "❌ YOUTUBE_API_KEY não encontrada."
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
    # SETUP HOOK
    # =====================================================

    async def setup_hook(self):

        print(
            "🔵 SETUP HOOK INICIADO",
            flush=True
        )


        # -------------------------------------------------
        # BANCO
        # -------------------------------------------------

        print(
            "🔄 Inicializando banco de dados...",
            flush=True
        )

        criar_banco()

        print(
            "   ✅ Banco de dados pronto!",
            flush=True
        )


        # -------------------------------------------------
        # GERAL
        # -------------------------------------------------

        print(
            "🔄 Carregando módulo geral...",
            flush=True
        )

        await self.load_extension(
            "cogs.geral"
        )

        print(
            "   ✅ geral carregado!",
            flush=True
        )


        # -------------------------------------------------
        # CONFIGURAÇÃO
        # -------------------------------------------------

        print(
            "🔄 Carregando módulo configuracao...",
            flush=True
        )

        await self.load_extension(
            "cogs.configuracao"
        )

        print(
            "   ✅ configuracao carregado!",
            flush=True
        )


        # -------------------------------------------------
        # YOUTUBE
        # -------------------------------------------------

        print(
            "🔄 Carregando módulo youtube...",
            flush=True
        )

        await self.load_extension(
            "cogs.youtube"
        )

        print(
            "   ✅ youtube carregado!",
            flush=True
        )


        # -------------------------------------------------
        # SINCRONIZAR SLASH COMMANDS
        # -------------------------------------------------

        print(
            "🔄 Sincronizando comandos...",
            flush=True
        )

        synced = await self.tree.sync()

        print(
            f"✅ {len(synced)} comando(s) sincronizado(s)!",
            flush=True
        )


        for command in synced:

            print(
                f"   └─ /{command.name}",
                flush=True
            )


        print(
            "🟢 SETUP HOOK FINALIZADO",
            flush=True
        )


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
# ERRO DOS SLASH COMMANDS
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

    print("=" * 60)
    print()


    try:

        if not interaction.response.is_done():

            await interaction.response.send_message(
                "❌ Ocorreu um erro ao executar este comando.",
                ephemeral=True
            )

        else:

            await interaction.followup.send(
                "❌ Ocorreu um erro ao executar este comando.",
                ephemeral=True
            )

    except Exception as erro_resposta:

        print(
            f"❌ Não foi possível enviar "
            f"a mensagem de erro: {erro_resposta}"
        )


# =========================================================
# INICIALIZAÇÃO
# =========================================================

print(
    "🚀 Iniciando Evelly...",
    flush=True
)


bot.run(
    DISCORD_TOKEN
)