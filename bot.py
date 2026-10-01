import os
import asyncio
import traceback
from datetime import datetime, timezone

import discord
from discord.ext import commands

from dotenv import load_dotenv
from supabase import create_client

from database.database import criar_banco


# ============================================================
# CARREGAR .ENV
# ============================================================

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")


# ============================================================
# RICH PRESENCE DA EVELLY
# ============================================================

PRESENCE_ENABLED = True

# Status do Discord
# online / idle / dnd / invisible
PRESENCE_STATUS = "online"

# Tipo da atividade
# playing / watching / listening / competing
PRESENCE_TYPE = "playing"


# ============================================================
# INFORMAÃ‡Ã•ES DA EVELLY
# ============================================================

PRESENCE_NAME = "Evelly"

PRESENCE_DETAILS = "Competitivo"

PRESENCE_STATE = "Jogando Blood Strike"


# ============================================================
# IMAGEM GRANDE
# ============================================================
#
# OpÃ§Ã£o C escolhida:
#
# chatgpt_image_15_de_set_de_2026_16_25_50
#
# Essa serÃ¡ a imagem principal da Presence.
#

PRESENCE_LARGE_IMAGE = (
    "chatgpt_image_15_de_set_de_2026_16_25_50"
)

PRESENCE_LARGE_TEXT = "Evelly â€¢ LN"


# ============================================================
# IMAGEM PEQUENA
# ============================================================
#
# Usando o logo do Blood Strike.
#

PRESENCE_SMALL_IMAGE = "blood_strike_logo_"

PRESENCE_SMALL_TEXT = "Blood Strike"


# ============================================================
# PARTY
# ============================================================
#
# Discord exibirÃ¡:
#
# 1 de 4
#

PRESENCE_PARTY_ID = "evelly-main"

PRESENCE_PARTY_CURRENT = 1
PRESENCE_PARTY_MAX = 4


# ============================================================
# TIMER PERSISTENTE
# ============================================================
#
# O horÃ¡rio fica salvo no Supabase.
#
# Portanto:
#
# Evelly inicia
#       â†“
# salva horÃ¡rio
#       â†“
# GitHub reinicia
#       â†“
# Evelly volta
#       â†“
# recupera horÃ¡rio
#       â†“
# contador continua
#

PRESENCE_PERSIST_TIMER = True


# ============================================================
# RESET DO TIMER
# ============================================================
#
# False = mantÃ©m o contador atual.
#
# True = cria um novo inÃ­cio.
#
# Deixe False normalmente.
#

PRESENCE_RESET_TIMER = False


# ============================================================
# SUPABASE
# ============================================================

PRESENCE_TABLE = "evelly_presence"

SUPABASE_URL = os.getenv("SUPABASE_URL")

SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_PUBLISHABLE_KEY")
)

presence_supabase = None


if SUPABASE_URL and SUPABASE_KEY:

    try:

        presence_supabase = create_client(
            SUPABASE_URL,
            SUPABASE_KEY
        )

    except Exception as erro:

        print(
            f"âš ï¸ NÃ£o foi possÃ­vel iniciar Supabase "
            f"da presenÃ§a: {erro}",
            flush=True
        )


# ============================================================
# CARREGAR INÃCIO DA PRESENCE
# ============================================================

async def carregar_inicio_presenca():

    agora = datetime.now(timezone.utc)

    # --------------------------------------------------------
    # Timer nÃ£o persistente
    # --------------------------------------------------------

    if not PRESENCE_PERSIST_TIMER:

        return agora


    # --------------------------------------------------------
    # Supabase indisponÃ­vel
    # --------------------------------------------------------

    if presence_supabase is None:

        print(
            "âš ï¸ Supabase da presenÃ§a indisponÃ­vel.",
            flush=True
        )

        print(
            "âš ï¸ O contador desta sessÃ£o nÃ£o serÃ¡ persistente.",
            flush=True
        )

        return agora


    try:

        # ====================================================
        # FORÃ‡AR NOVO TIMER
        # ====================================================

        if PRESENCE_RESET_TIMER:

            (
                presence_supabase
                .table(PRESENCE_TABLE)
                .upsert({
                    "id": 1,
                    "started_at": agora.isoformat(),
                    "updated_at": agora.isoformat(),
                })
                .execute()
            )

            print(
                "ðŸ”„ Contador da Rich Presence reiniciado!",
                flush=True
            )

            return agora


        # ====================================================
        # BUSCAR TIMER EXISTENTE
        # ====================================================

        resposta = (
            presence_supabase
            .table(PRESENCE_TABLE)
            .select("started_at")
            .eq("id", 1)
            .limit(1)
            .execute()
        )


        # ====================================================
        # TIMER ENCONTRADO
        # ====================================================

        if resposta.data:

            valor = resposta.data[0].get(
                "started_at"
            )


            if valor:

                inicio = datetime.fromisoformat(
                    str(valor).replace(
                        "Z",
                        "+00:00"
                    )
                )


                if inicio.tzinfo is None:

                    inicio = inicio.replace(
                        tzinfo=timezone.utc
                    )


                print(
                    "â±ï¸ Rich Presence retomada desde: "
                    f"{inicio.isoformat()}",
                    flush=True
                )


                return inicio


        # ====================================================
        # CRIAR NOVO TIMER
        # ====================================================

        (
            presence_supabase
            .table(PRESENCE_TABLE)
            .upsert({
                "id": 1,
                "started_at": agora.isoformat(),
                "updated_at": agora.isoformat(),
            })
            .execute()
        )


        print(
            "ðŸ†• Novo contador da Rich Presence iniciado:",
            flush=True
        )

        print(
            agora.isoformat(),
            flush=True
        )


        return agora


    except Exception as erro:

        print(
            "âš ï¸ Erro ao recuperar contador "
            f"da Rich Presence: {erro}",
            flush=True
        )

        return agora


# ============================================================
# CONSTRUIR RICH PRESENCE
# ============================================================

def construir_atividade_presenca(inicio):

    tipos = {

        "playing":
            discord.ActivityType.playing,

        "watching":
            discord.ActivityType.watching,

        "listening":
            discord.ActivityType.listening,

        "competing":
            discord.ActivityType.competing,
    }


    tipo = tipos.get(

        str(
            PRESENCE_TYPE
        ).lower(),

        discord.ActivityType.playing
    )


    # ========================================================
    # ASSETS
    # ========================================================

    assets = {}


    # Imagem grande

    if PRESENCE_LARGE_IMAGE:

        assets["large_image"] = (
            PRESENCE_LARGE_IMAGE
        )


    if PRESENCE_LARGE_TEXT:

        assets["large_text"] = (
            PRESENCE_LARGE_TEXT
        )


    # Imagem pequena

    if PRESENCE_SMALL_IMAGE:

        assets["small_image"] = (
            PRESENCE_SMALL_IMAGE
        )


    if PRESENCE_SMALL_TEXT:

        assets["small_text"] = (
            PRESENCE_SMALL_TEXT
        )


    # ========================================================
    # PARTY
    # ========================================================

    party = {}


    if PRESENCE_PARTY_ID:

        party["id"] = (
            PRESENCE_PARTY_ID
        )


    if (
        PRESENCE_PARTY_CURRENT is not None
        and
        PRESENCE_PARTY_MAX is not None
    ):

        party["size"] = [

            int(
                PRESENCE_PARTY_CURRENT
            ),

            int(
                PRESENCE_PARTY_MAX
            )
        ]


    # ========================================================
    # DADOS DA ACTIVITY
    # ========================================================

    dados = {

        "type":
            tipo,

        "name":
            PRESENCE_NAME,
    }


    if PRESENCE_DETAILS:

        dados["details"] = (
            PRESENCE_DETAILS
        )


    if PRESENCE_STATE:

        dados["state"] = (
            PRESENCE_STATE
        )


    if assets:

        dados["assets"] = assets


    if party:

        dados["party"] = party


    # ========================================================
    # TIMESTAMP
    # ========================================================

    if (
        PRESENCE_PERSIST_TIMER
        and
        inicio
    ):

        dados["timestamps"] = {

            "start":
                int(
                    inicio.timestamp()
                    * 1000
                )
        }


    # ========================================================
    # CRIAR ACTIVITY
    # ========================================================

    return discord.Activity(
        **dados
    )


# ============================================================
# OBTER STATUS
# ============================================================

def obter_status_presenca():

    mapa = {

        "online":
            discord.Status.online,

        "idle":
            discord.Status.idle,

        "dnd":
            discord.Status.dnd,

        "invisible":
            discord.Status.invisible,
    }


    return mapa.get(

        str(
            PRESENCE_STATUS
        ).lower(),

        discord.Status.online
    )


# ============================================================
# VALIDAR CONFIGURAÃ‡Ã•ES
# ============================================================

if not DISCORD_TOKEN:

    raise RuntimeError(
        "âŒ DISCORD_TOKEN nÃ£o foi encontrado no .env"
    )


if not YOUTUBE_API_KEY:

    raise RuntimeError(
        "âŒ YOUTUBE_API_KEY nÃ£o foi encontrado no .env"
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

        self.youtube_api_key = (
            YOUTUBE_API_KEY
        )


    # ========================================================
    # CARREGAR SISTEMAS
    # ========================================================

    async def setup_hook(self):
        print(
            "==============================================",
            flush=True
        )

        print(
            "ðŸ”„ CARREGANDO SISTEMAS DA EVELLY",
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
                "ðŸ—„ï¸ Conectando ao Supabase...",
                flush=True
            )

            criar_banco()

            print(
                "â˜ï¸ Banco Supabase conectado!",
                flush=True
            )


        except Exception as erro:

            print(
                "==============================================",
                flush=True
            )

            print(
                "âŒ ERRO AO CONECTAR AO BANCO",
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

            "cogs.ticket",

            "cogs.sugestao",

            "cogs.evelly",

            "cogs.limpar",

            "cogs.atualizacoes",

            "cogs.sticky",


            "cogs.embed",
#
        ]


        # ====================================================
        # CARREGAR COGS
        # ====================================================

        for cog in cogs:

            print(
                f"ðŸ”„ Carregando: {cog}",
                flush=True
            )


            try:

                await self.load_extension(
                    cog
                )


                print(
                    f"âœ… Sistema carregado: {cog}",
                    flush=True
                )


            except Exception as erro:

                print(
                    "==============================================",
                    flush=True
                )

                print(
                    f"âŒ ERRO AO CARREGAR: {cog}",
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
            "âœ… TODOS OS SISTEMAS FORAM PROCESSADOS!",
            flush=True
        )

        print(
            "==============================================",
            flush=True
        )


    # ========================================================
    # ATUALIZAR PRESENCE
    # ========================================================

    async def atualizar_presenca(self):

        if not PRESENCE_ENABLED:

            print(
                "â„¹ï¸ Rich Presence desativada.",
                flush=True
            )

            return


        try:

            # ------------------------------------------------
            # Recuperar inÃ­cio persistente
            # ------------------------------------------------

            inicio = (
                await carregar_inicio_presenca()
            )


            # ------------------------------------------------
            # Construir Activity
            # ------------------------------------------------

            atividade = (
                construir_atividade_presenca(
                    inicio
                )
            )


            # ------------------------------------------------
            # Status
            # ------------------------------------------------

            status = (
                obter_status_presenca()
            )


            # ------------------------------------------------
            # Enviar ao Discord
            # ------------------------------------------------

            await self.change_presence(

                status=status,

                activity=atividade
            )


            # ------------------------------------------------
            # LOG
            # ------------------------------------------------

            print(
                "ðŸ’œ Rich Presence da Evelly atualizada!",
                flush=True
            )

            print(
                f"   â”œâ”€ Tipo: {PRESENCE_TYPE}",
                flush=True
            )

            print(
                f"   â”œâ”€ Nome: {PRESENCE_NAME}",
                flush=True
            )

            print(
                f"   â”œâ”€ Detalhes: {PRESENCE_DETAILS}",
                flush=True
            )

            print(
                f"   â”œâ”€ Estado: {PRESENCE_STATE}",
                flush=True
            )

            print(
                f"   â”œâ”€ Party: "
                f"{PRESENCE_PARTY_CURRENT} de "
                f"{PRESENCE_PARTY_MAX}",
                flush=True
            )

            print(
                "   â”œâ”€ Imagem grande: "
                f"{PRESENCE_LARGE_IMAGE}",
                flush=True
            )

            print(
                "   â”œâ”€ Imagem pequena: "
                f"{PRESENCE_SMALL_IMAGE}",
                flush=True
            )

            print(
                "   â””â”€ Timer persistente: "
                f"{'SIM' if PRESENCE_PERSIST_TIMER else 'NÃƒO'}",
                flush=True
            )


        except Exception as erro:

            print(
                f"âš ï¸ Erro ao atualizar presenÃ§a: {erro}",
                flush=True
            )

            traceback.print_exc()


    # ========================================================
    # BOT ONLINE
    # ========================================================

    async def on_ready(self):

        print(
            "==============================================",
            flush=True
        )

        print(
            "ðŸ¤– BOT ONLINE!",
            flush=True
        )

        print(
            f"ðŸ‘¤ Nome: {self.user}",
            flush=True
        )

        print(
            f"ðŸ†” ID: {self.user.id}",
            flush=True
        )

        print(
            f"ðŸŒ Servidores: {len(self.guilds)}",
            flush=True
        )

        print(
            "==============================================",
            flush=True
        )


        # ====================================================
        # PRESENCE
        # ====================================================

        await self.atualizar_presenca()


        # ====================================================
        # SINCRONIZAR SLASH COMMANDS
        # ====================================================

        for guild in self.guilds:

            try:

                print(
                    f"ðŸ”„ Sincronizando comandos: {guild.name}",
                    flush=True
                )


                self.tree.copy_global_to(
                    guild=guild
                )


                comandos = await self.tree.sync(
                    guild=guild
                )


                print(
                    "âœ… Comandos sincronizados!",
                    flush=True
                )

                print(
                    f"ðŸ“‹ Total: {len(comandos)}",
                    flush=True
                )


                for comando in comandos:

                    try:

                        nome = (
                            comando.qualified_name
                        )

                    except Exception:

                        nome = comando.name


                    print(
                        f"   â””â”€ /{nome}",
                        flush=True
                    )


            except Exception as erro:

                print(
                    "==============================================",
                    flush=True
                )

                print(
                    f"âŒ ERRO AO SINCRONIZAR "
                    f"{guild.name}",
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
            "ðŸŸ¢ EVELLY ESTÃ FUNCIONANDO!",
            flush=True
        )

        print(
            "ðŸ“¦ Sistema de posts: ATIVO",
            flush=True
        )

        print(
            "ðŸ“º Sistema YouTube: ATIVO",
            flush=True
        )

        print(
            "ðŸ“ž Sistema de call: ATIVO",
            flush=True
        )

        print(
            "ðŸ“¨ Sistema EnviarPV: ATIVO",
            flush=True
        )

        print(
            "ðŸ”— Sistema LinkNot: ATIVO",
            flush=True
        )

        print(
            "ðŸ’œ Sistema de boas-vindas: ATIVO",
            flush=True
        )

        print(
            "ðŸ”‡ Sistema de mÃºsica: REMOVIDO",
            flush=True
        )

        print(
            "ðŸ’œ PresenÃ§a Discord: ATIVA",
            flush=True
        )

        print(
            "ðŸ–¼ï¸ Asset grande: "
            "chatgpt_image_15_de_set_de_2026_16_25_50",
            flush=True
        )

        print(
            "ðŸŽ® Asset pequeno: blood_strike_logo_",
            flush=True
        )

        print(
            "ðŸ—„ï¸ Supabase: ATIVO",
            flush=True
        )

        print(
            "â±ï¸ Timer persistente: ATIVO",
            flush=True
        )

        print(
            "â±ï¸ ReinÃ­cio automÃ¡tico: 5h30",
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
            "âŒ ERRO GERAL DA EVELLY",
            flush=True
        )

        print(
            f"ðŸ“Œ Evento: {event_method}",
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
# REINÃCIO AUTOMÃTICO
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
        "â±ï¸ SISTEMA DE REINÃCIO AUTOMÃTICO",
        flush=True
    )

    print(
        "ðŸ”„ Ciclo configurado: 5 horas e 30 minutos",
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
            "ðŸ”„ REINÃCIO AUTOMÃTICO",
            flush=True
        )

        print(
            "â±ï¸ Ciclo de 5h30 concluÃ­do.",
            flush=True
        )

        print(
            "ðŸ›‘ Encerrando conexÃ£o da Evelly...",
            flush=True
        )

        print(
            "ðŸ“¡ GitHub Actions deverÃ¡ iniciar "
            "o prÃ³ximo ciclo.",
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
            "â¹ï¸ Contador de reinÃ­cio cancelado.",
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
        "ðŸš€ INICIANDO EVELLY",
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
            "âŒ TOKEN DO DISCORD INVÃLIDO",
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
            "âŒ ERRO AO INICIAR A EVELLY",
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
            "ðŸ›‘ EVELLY ENCERRADA MANUALMENTE",
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
            "ðŸ’€ ERRO FATAL",
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




