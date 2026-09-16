import os
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from supabase import create_client


# ============================================================
# CONFIGURAÇÃO
# ============================================================

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")

SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_PUBLISHABLE_KEY")
)

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "❌ SUPABASE_URL e uma chave do Supabase precisam "
        "estar configuradas no .env."
    )

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


# ============================================================
# CATEGORIAS
# ============================================================

CATEGORIAS_VALIDAS = {
    "youtube",
    "twitch",
    "instagram",
    "tiktok",
    "facebook",
    "x",
    "twitter",
    "discord",
    "sites",
    "nenhum",
    "todos",
}


NOMES_CATEGORIAS = {
    "youtube": "YouTube",
    "twitch": "Twitch",
    "instagram": "Instagram",
    "tiktok": "TikTok",
    "facebook": "Facebook",
    "x": "X/Twitter",
    "twitter": "X/Twitter",
    "discord": "Discord",
    "sites": "Sites",
    "nenhum": "Nenhum",
    "todos": "Todos",
}


DOMINIOS = {
    "youtube": (
        "youtube.com",
        "www.youtube.com",
        "youtu.be",
        "www.youtu.be",
        "youtube-nocookie.com",
    ),

    "twitch": (
        "twitch.tv",
        "www.twitch.tv",
    ),

    "instagram": (
        "instagram.com",
        "www.instagram.com",
    ),

    "tiktok": (
        "tiktok.com",
        "www.tiktok.com",
    ),

    "facebook": (
        "facebook.com",
        "www.facebook.com",
        "fb.watch",
        "www.fb.watch",
    ),

    "x": (
        "x.com",
        "www.x.com",
        "twitter.com",
        "www.twitter.com",
    ),

    "discord": (
        "discord.gg",
        "discord.com",
        "www.discord.com",
        "discordapp.com",
        "www.discordapp.com",
    ),
}


URL_REGEX = re.compile(
    r"https?://[^\s<>()]+",
    re.IGNORECASE
)


# ============================================================
# URL
# ============================================================

def extrair_urls(texto: str):
    if not texto:
        return []

    urls = URL_REGEX.findall(texto)

    resultado = []

    for url in urls:

        url = url.rstrip(
            ".,!?;:)]}"
        )

        if url not in resultado:
            resultado.append(url)

    return resultado


def normalizar_host(url: str):

    try:

        parsed = urlparse(url)

        host = parsed.netloc.lower().strip()

        if "@" in host:
            host = host.split("@", 1)[1]

        if ":" in host:
            host = host.split(":", 1)[0]

        return host

    except Exception:

        return ""


def detectar_categoria(url: str):

    host = normalizar_host(url)

    if not host:
        return "sites"

    for categoria, dominios in DOMINIOS.items():

        for dominio in dominios:

            if (
                host == dominio
                or host.endswith("." + dominio)
            ):
                return categoria

    return "sites"


def nome_categoria(categoria: str):

    return NOMES_CATEGORIAS.get(
        categoria,
        categoria.title()
    )


# ============================================================
# CATEGORIAS CONFIGURADAS
# ============================================================

def parsear_categorias(texto: str):

    if not texto:
        return []

    texto = (
        texto.lower()
        .replace("/", " ")
        .replace(",", " ")
        .replace(";", " ")
        .replace("|", " ")
    )

    partes = texto.split()

    categorias = []

    for parte in partes:

        parte = parte.strip()

        if not parte:
            continue

        if parte == "x/twitter":
            parte = "x"

        if parte == "x-twitter":
            parte = "x"

        if parte == "todos":
            return ["todos"]

        if parte == "nenhum":
            return ["nenhum"]

        if parte in CATEGORIAS_VALIDAS:

            if parte not in categorias:
                categorias.append(parte)

    return categorias


# ============================================================
# CARGOS
# ============================================================

def parsear_cargos(
    guild: discord.Guild,
    texto: str
):

    if not texto:
        return []

    ids = []

    mencoes = re.findall(
        r"<@&(\d+)>",
        texto
    )

    for valor in mencoes:

        try:

            role_id = int(valor)

            if guild.get_role(role_id):

                if role_id not in ids:
                    ids.append(role_id)

        except Exception:
            pass

    numeros = re.findall(
        r"\b\d{15,25}\b",
        texto
    )

    for valor in numeros:

        try:

            role_id = int(valor)

            if guild.get_role(role_id):

                if role_id not in ids:
                    ids.append(role_id)

        except Exception:
            pass

    return ids


# ============================================================
# PERMISSÕES
# ============================================================

def pode_configurar(
    interaction: discord.Interaction
):

    if interaction.guild is None:
        return False

    usuario = interaction.user

    if not isinstance(
        usuario,
        discord.Member
    ):
        return False

    if usuario.guild_permissions.administrator:
        return True

    if usuario.guild_permissions.manage_guild:
        return True

    if usuario.guild_permissions.manage_messages:
        return True

    return False


def verificar_permissao():

    async def predicate(
        interaction: discord.Interaction
    ):

        if pode_configurar(interaction):
            return True

        raise app_commands.CheckFailure(
            "Você não possui permissão para configurar a moderação."
        )

    return app_commands.check(predicate)


# ============================================================
# SUPABASE
# ============================================================

def obter_config(
    guild_id: int,
    channel_id: int
):

    resposta = (
        supabase
        .table("linknot_config")
        .select("*")
        .eq("guild_id", guild_id)
        .eq("channel_id", channel_id)
        .limit(1)
        .execute()
    )

    if not resposta.data:
        return None

    return resposta.data[0]


def obter_configs_guild(
    guild_id: int
):

    resposta = (
        supabase
        .table("linknot_config")
        .select("*")
        .eq("guild_id", guild_id)
        .order("channel_id")
        .execute()
    )

    return resposta.data or []


def salvar_config(
    guild_id: int,
    channel_id: int,
    categorias,
    role_ids,
    warning_message,
    log_channel_id,
    delete_message=True,
    enabled=True,
):

    dados = {
        "guild_id": guild_id,
        "channel_id": channel_id,
        "allowed_categories": categorias,
        "role_ids": role_ids,
        "warning_message": warning_message,
        "log_channel_id": log_channel_id,
        "delete_message": delete_message,
        "enabled": enabled,
        "updated_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    resposta = (
        supabase
        .table("linknot_config")
        .upsert(
            dados,
            on_conflict="guild_id,channel_id"
        )
        .execute()
    )

    return resposta


def registrar_log(
    guild_id: int,
    channel_id: int,
    user_id: int,
    message_id: int,
    username: str,
    display_name: str,
    action: str,
    reason: str,
    content: str,
    sent_at,
    deleted_at,
    attachments,
    urls,
    metadata=None,
):

    dados = {
        "guild_id": guild_id,
        "channel_id": channel_id,
        "user_id": user_id,
        "message_id": message_id,
        "username": username,
        "display_name": display_name,
        "action": action,
        "reason": reason,
        "content": content,
        "sent_at": (
            sent_at.isoformat()
            if sent_at
            else None
        ),
        "deleted_at": (
            deleted_at.isoformat()
            if deleted_at
            else None
        ),
        "attachments": attachments,
        "urls": urls,
        "metadata": metadata or {},
    }

    try:

        (
            supabase
            .table("moderation_logs")
            .insert(dados)
            .execute()
        )

    except Exception as erro:

        print(
            f"[LINKNOT] Erro ao salvar log no Supabase: {erro}",
            flush=True
        )


# ============================================================
# ANEXOS
# ============================================================

def coletar_anexos(
    message: discord.Message
):

    resultado = []

    for attachment in message.attachments:

        resultado.append(
            {
                "filename": attachment.filename,
                "url": attachment.url,
                "content_type": attachment.content_type,
                "size": attachment.size,
            }
        )

    return resultado


# ============================================================
# VERIFICAR LINK
# ============================================================

def url_permitida(
    url: str,
    categorias
):

    categorias = [
        str(c).lower()
        for c in categorias
    ]

    if "todos" in categorias:
        return True

    if "nenhum" in categorias:
        return False

    if "sites" in categorias:
        return True

    categoria_detectada = detectar_categoria(
        url
    )

    return categoria_detectada in categorias


def mensagem_permitida(
    urls,
    categorias
):

    if not urls:
        return True, None

    for url in urls:

        if not url_permitida(
            url,
            categorias
        ):

            categoria = detectar_categoria(
                url
            )

            return False, categoria

    return True, None


# ============================================================
# MENCIONAR CARGOS
# ============================================================

def montar_mencoes_roles(
    guild: discord.Guild,
    role_ids
):

    mencoes = []

    for role_id in role_ids:

        role = guild.get_role(
            int(role_id)
        )

        if role:
            mencoes.append(
                role.mention
            )

    return " ".join(mencoes)


# ============================================================
# LOG NO DISCORD
# ============================================================

async def enviar_log_discord(
    guild: discord.Guild,
    config,
    message: discord.Message,
    reason: str,
    urls,
    attachments,
    sent_at,
    deleted_at,
):

    log_channel_id = config.get(
        "log_channel_id"
    )

    if not log_channel_id:
        return

    canal = guild.get_channel(
        int(log_channel_id)
    )

    if canal is None:
        return

    if deleted_at and sent_at:

        diferenca = (
            deleted_at - sent_at
        ).total_seconds()

        tempo = f"{diferenca:.2f}s"

    else:

        tempo = "N/A"

    embed = discord.Embed(
        title="🛡️ EVELLY • MODERAÇÃO",
        description="🗑️ **Mensagem removida**",
        color=discord.Color.red(),
        timestamp=(
            deleted_at
            or discord.utils.utcnow()
        ),
    )

    # ========================================================
    # USUÁRIO
    # ========================================================

    embed.add_field(
        name="👤 Usuário",
        value=(
            f"{message.author.mention}\n"
            f"`{message.author}`\n"
            f"ID: `{message.author.id}`"
        ),
        inline=False,
    )

    # ========================================================
    # CANAL
    # ========================================================

    embed.add_field(
        name="📍 Canal",
        value=message.channel.mention,
        inline=True,
    )

    # ========================================================
    # ID
    # ========================================================

    embed.add_field(
        name="🆔 Mensagem",
        value=f"`{message.id}`",
        inline=True,
    )

    # ========================================================
    # HORÁRIO ENVIO
    # ========================================================

    embed.add_field(
        name="🕐 Enviada",
        value=(
            f"<t:{int(sent_at.timestamp())}:F>\n"
            f"<t:{int(sent_at.timestamp())}:T>"
        ),
        inline=True,
    )

    # ========================================================
    # HORÁRIO REMOÇÃO
    # ========================================================

    embed.add_field(
        name="🗑️ Removida",
        value=(
            f"<t:{int(deleted_at.timestamp())}:F>\n"
            f"<t:{int(deleted_at.timestamp())}:T>"
        ),
        inline=True,
    )

    # ========================================================
    # TEMPO
    # ========================================================

    embed.add_field(
        name="⚡ Tempo até remoção",
        value=f"`{tempo}`",
        inline=True,
    )

    # ========================================================
    # MOTIVO
    # ========================================================

    embed.add_field(
        name="🔗 Motivo",
        value=reason[:1024],
        inline=False,
    )

    # ========================================================
    # LINKS
    # ========================================================

    if urls:

        texto_urls = "\n".join(
            f"• {url}"
            for url in urls
        )

        if len(texto_urls) > 1024:
            texto_urls = (
                texto_urls[:1000]
                + "..."
            )

        embed.add_field(
            name="🔗 Links detectados",
            value=texto_urls,
            inline=False,
        )

    # ========================================================
    # CONTEÚDO
    # ========================================================

    conteudo = (
        message.content
        if message.content
        else "*(sem texto)*"
    )

    if len(conteudo) > 1024:
        conteudo = (
            conteudo[:1000]
            + "..."
        )

    embed.add_field(
        name="💬 Conteúdo",
        value=conteudo,
        inline=False,
    )

    # ========================================================
    # ANEXOS
    # ========================================================

    if attachments:

        anexos_texto = []

        for anexo in attachments:

            nome = anexo.get(
                "filename",
                "arquivo"
            )

            url = anexo.get(
                "url",
                ""
            )

            content_type = (
                anexo.get(
                    "content_type"
                )
                or "desconhecido"
            )

            anexos_texto.append(
                f"📎 [{nome}]({url})\n"
                f"`{content_type}`"
            )

        texto_anexos = (
            "\n\n".join(
                anexos_texto
            )
        )

        if len(texto_anexos) > 1024:

            texto_anexos = (
                texto_anexos[:1000]
                + "..."
            )

        embed.add_field(
            name="📎 Anexos",
            value=texto_anexos,
            inline=False,
        )

        # ====================================================
        # MOSTRAR PRIMEIRA IMAGEM
        # ====================================================

        for anexo in attachments:

            content_type = (
                anexo.get(
                    "content_type"
                )
                or ""
            )

            if content_type.startswith(
                "image/"
            ):

                try:

                    embed.set_image(
                        url=anexo["url"]
                    )

                except Exception:
                    pass

                break

    embed.set_footer(
        text="Evelly • LinkNot / Moderação"
    )

    try:

        await canal.send(
            embed=embed,
            allowed_mentions=discord.AllowedMentions.none()
        )

    except Exception as erro:

        print(
            f"[LINKNOT] Erro ao enviar log Discord: {erro}",
            flush=True
        )


# ============================================================
# COG
# ============================================================

class LinkNot(commands.Cog):

    def __init__(
        self,
        bot
    ):

        self.bot = bot

        print(
            "🔗 Sistema LinkNot carregado.",
            flush=True
        )

    # ========================================================
    # /LINKNOT
    # ========================================================

    @app_commands.command(
        name="linknot",
        description="Configura a moderação de links de um canal."
    )
    @app_commands.describe(
        canal="Canal onde a regra será aplicada.",
        categoria=(
            "Ex: YouTube | Twitch | Instagram,TikTok | "
            "Sites | Nenhum | Todos"
        ),
        cargos=(
            "Cargos que serão mencionados na mensagem."
        ),
        mensagem=(
            "Mensagem enviada quando um link for bloqueado."
        ),
        log_canal=(
            "Canal específico para os logs desta regra."
        ),
    )
    @verificar_permissao()
    async def linknot(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel,
        categoria: str,
        cargos: str,
        mensagem: str = None,
        log_canal: discord.TextChannel = None,
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                "❌ Este comando só pode ser usado em um servidor.",
                ephemeral=True,
            )

            return

        categorias = parsear_categorias(
            categoria
        )

        if not categorias:

            await interaction.response.send_message(
                "❌ Categoria inválida.\n\n"
                "Use:\n"
                "YouTube, Twitch, Instagram, TikTok, "
                "Facebook, X/Twitter, Discord, Sites, "
                "Nenhum ou Todos.",
                ephemeral=True,
            )

            return

        role_ids = parsear_cargos(
            interaction.guild,
            cargos
        )

        if not role_ids:

            await interaction.response.send_message(
                "❌ Não encontrei nenhum cargo válido.\n\n"
                "Mencione os cargos, por exemplo:\n"
                "`@Moderadores @Staff`",
                ephemeral=True,
            )

            return

        if mensagem is None:

            mensagem = (
                "❌ Você não pode enviar este tipo "
                "de link neste canal."
            )

        if len(mensagem) > 1000:

            await interaction.response.send_message(
                "❌ A mensagem pode ter no máximo "
                "**1000 caracteres**.",
                ephemeral=True,
            )

            return

        # ====================================================
        # SE NÃO FOR INFORMADO:
        # TENTA USAR O CANAL GLOBAL ATUAL
        # ====================================================

        if log_canal is None:

            configs_existentes = obter_configs_guild(
                interaction.guild.id
            )

            log_global = None

            for config in configs_existentes:

                if config.get(
                    "log_channel_id"
                ):

                    log_global = interaction.guild.get_channel(
                        int(
                            config[
                                "log_channel_id"
                            ]
                        )
                    )

                    if log_global:
                        break

            if log_global:

                log_canal = log_global

            else:

                log_canal = interaction.channel

        try:

            salvar_config(
                guild_id=interaction.guild.id,
                channel_id=canal.id,
                categorias=categorias,
                role_ids=role_ids,
                warning_message=mensagem,
                log_channel_id=log_canal.id,
                delete_message=True,
                enabled=True,
            )

        except Exception as erro:

            print(
                f"[LINKNOT] Erro ao salvar configuração: {erro}",
                flush=True
            )

            await interaction.response.send_message(
                "❌ Não consegui salvar a configuração "
                "no Supabase.",
                ephemeral=True,
            )

            return

        categorias_texto = ", ".join(
            nome_categoria(c)
            for c in categorias
        )

        cargos_texto = " ".join(
            interaction.guild.get_role(
                role_id
            ).mention
            for role_id in role_ids
            if interaction.guild.get_role(
                role_id
            )
        )

        embed = discord.Embed(
            title="🔗 EVELLY • LINKNOT",
            description=(
                "A regra de moderação foi configurada "
                "com sucesso."
            ),
            color=discord.Color.green(),
        )

        embed.add_field(
            name="📍 Canal",
            value=canal.mention,
            inline=True,
        )

        embed.add_field(
            name="🔗 Links permitidos",
            value=categorias_texto,
            inline=True,
        )

        embed.add_field(
            name="👮 Cargos",
            value=cargos_texto,
            inline=False,
        )

        embed.add_field(
            name="🗑️ Exclusão automática",
            value="🟢 Ativada",
            inline=True,
        )

        embed.add_field(
            name="📋 Canal de logs",
            value=log_canal.mention,
            inline=True,
        )

        embed.add_field(
            name="💬 Mensagem",
            value=mensagem,
            inline=False,
        )

        embed.set_footer(
            text="Evelly • LinkNot"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )

        # ====================================================
        # REGISTRAR CONFIGURAÇÃO
        # ====================================================

        registrar_log(
            guild_id=interaction.guild.id,
            channel_id=canal.id,
            user_id=interaction.user.id,
            message_id=0,
            username=str(interaction.user),
            display_name=interaction.user.display_name,
            action="linknot_config_created_or_updated",
            reason="Regra LinkNot criada ou atualizada.",
            content="",
            sent_at=None,
            deleted_at=None,
            attachments=[],
            urls=[],
            metadata={
                "configured_channel_id": canal.id,
                "allowed_categories": categorias,
                "role_ids": role_ids,
                "log_channel_id": log_canal.id,
                "enabled": True,
                "delete_message": True,
            },
        )

        print(
            f"[LINKNOT] Configurado | "
            f"guild={interaction.guild.id} | "
            f"canal={canal.id} | "
            f"log={log_canal.id} | "
            f"categorias={categorias}",
            flush=True,
        )

    # ========================================================
    # /LINKNOT_LOG
    # ========================================================

    @app_commands.command(
        name="linknot_log",
        description="Define o canal onde os logs do LinkNot serão enviados."
    )
    @app_commands.describe(
        canal="Canal onde a Evelly enviará os logs de moderação."
    )
    @verificar_permissao()
    async def linknot_log(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel,
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                "❌ Use este comando dentro de um servidor.",
                ephemeral=True,
            )

            return

        try:

            configs = obter_configs_guild(
                interaction.guild.id
            )

            if not configs:

                await interaction.response.send_message(
                    "❌ Nenhuma regra LinkNot foi configurada ainda.\n\n"
                    "Primeiro configure uma regra com `/linknot`.",
                    ephemeral=True,
                )

                return

            quantidade = 0

            for config in configs:

                (
                    supabase
                    .table("linknot_config")
                    .update(
                        {
                            "log_channel_id": canal.id,
                            "updated_at": (
                                datetime.now(
                                    timezone.utc
                                ).isoformat()
                            ),
                        }
                    )
                    .eq(
                        "guild_id",
                        interaction.guild.id
                    )
                    .eq(
                        "channel_id",
                        config["channel_id"]
                    )
                    .execute()
                )

                quantidade += 1

        except Exception as erro:

            print(
                f"[LINKNOT] Erro configurando canal global de logs: {erro}",
                flush=True
            )

            await interaction.response.send_message(
                "❌ Não consegui configurar o canal de logs.",
                ephemeral=True,
            )

            return

        # ====================================================
        # REGISTRAR ALTERAÇÃO
        # ====================================================

        registrar_log(
            guild_id=interaction.guild.id,
            channel_id=canal.id,
            user_id=interaction.user.id,
            message_id=0,
            username=str(interaction.user),
            display_name=interaction.user.display_name,
            action="linknot_log_channel_changed",
            reason="Canal global de logs do LinkNot alterado.",
            content="",
            sent_at=None,
            deleted_at=None,
            attachments=[],
            urls=[],
            metadata={
                "log_channel_id": canal.id,
                "rules_updated": quantidade,
            },
        )

        embed = discord.Embed(
            title="📋 EVELLY • LOGS",
            description=(
                "O canal de logs do LinkNot foi "
                "configurado com sucesso."
            ),
            color=discord.Color.green(),
        )

        embed.add_field(
            name="📋 Canal de logs",
            value=canal.mention,
            inline=False,
        )

        embed.add_field(
            name="🔗 Regras atualizadas",
            value=f"`{quantidade}` regra(s)",
            inline=True,
        )

        embed.add_field(
            name="🛡️ Sistema",
            value="LinkNot",
            inline=True,
        )

        embed.set_footer(
            text="Evelly • Moderação"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )

        print(
            f"[LINKNOT] Canal global de logs alterado | "
            f"guild={interaction.guild.id} | "
            f"log={canal.id}",
            flush=True,
        )

    # ========================================================
    # /LINKNOT_LISTAR
    # ========================================================

    @app_commands.command(
        name="linknot_listar",
        description="Lista as regras LinkNot deste servidor."
    )
    @verificar_permissao()
    async def linknot_listar(
        self,
        interaction: discord.Interaction
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                "❌ Use este comando dentro de um servidor.",
                ephemeral=True,
            )

            return

        try:

            configs = obter_configs_guild(
                interaction.guild.id
            )

        except Exception as erro:

            print(
                f"[LINKNOT] Erro ao listar: {erro}",
                flush=True
            )

            await interaction.response.send_message(
                "❌ Não consegui consultar o Supabase.",
                ephemeral=True,
            )

            return

        if not configs:

            await interaction.response.send_message(
                "🔗 **LinkNot**\n\n"
                "Nenhuma regra está configurada neste servidor.",
                ephemeral=True,
            )

            return

        embed = discord.Embed(
            title="🔗 EVELLY • LINKNOT",
            description=(
                "Regras configuradas neste servidor:"
            ),
            color=discord.Color.blurple(),
        )

        for config in configs:

            canal = interaction.guild.get_channel(
                int(
                    config["channel_id"]
                )
            )

            if canal is None:

                canal_texto = (
                    f"Canal removido "
                    f"`{config['channel_id']}`"
                )

            else:

                canal_texto = canal.mention

            categorias = config.get(
                "allowed_categories",
                []
            )

            categorias_texto = ", ".join(
                nome_categoria(c)
                for c in categorias
            )

            status = (
                "🟢 Ativo"
                if config.get("enabled")
                else "🔴 Desativado"
            )

            log_channel_id = config.get(
                "log_channel_id"
            )

            log_channel = None

            if log_channel_id:

                log_channel = (
                    interaction.guild.get_channel(
                        int(log_channel_id)
                    )
                )

            log_texto = (
                log_channel.mention
                if log_channel
                else "Não configurado"
            )

            embed.add_field(
                name=canal_texto,
                value=(
                    f"**Status:** {status}\n"
                    f"**Permitidos:** "
                    f"{categorias_texto or 'Nenhum'}\n"
                    f"**Excluir:** "
                    f"{'Sim' if config.get('delete_message') else 'Não'}\n"
                    f"**Logs:** {log_texto}"
                ),
                inline=False,
            )

        embed.set_footer(
            text=f"Evelly • {len(configs)} regra(s)"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )

    # ========================================================
    # /LINKNOT_REMOVER
    # ========================================================

    @app_commands.command(
        name="linknot_remover",
        description="Remove a regra LinkNot de um canal."
    )
    @app_commands.describe(
        canal="Canal cuja regra será removida."
    )
    @verificar_permissao()
    async def linknot_remover(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel,
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                "❌ Use este comando dentro de um servidor.",
                ephemeral=True,
            )

            return

        try:

            config = obter_config(
                interaction.guild.id,
                canal.id
            )

            if not config:

                await interaction.response.send_message(
                    f"❌ Não existe regra LinkNot em "
                    f"{canal.mention}.",
                    ephemeral=True,
                )

                return

            (
                supabase
                .table("linknot_config")
                .delete()
                .eq(
                    "guild_id",
                    interaction.guild.id
                )
                .eq(
                    "channel_id",
                    canal.id
                )
                .execute()
            )

        except Exception as erro:

            print(
                f"[LINKNOT] Erro ao remover: {erro}",
                flush=True
            )

            await interaction.response.send_message(
                "❌ Não consegui remover a regra.",
                ephemeral=True,
            )

            return

        registrar_log(
            guild_id=interaction.guild.id,
            channel_id=canal.id,
            user_id=interaction.user.id,
            message_id=0,
            username=str(interaction.user),
            display_name=interaction.user.display_name,
            action="linknot_config_removed",
            reason="Regra LinkNot removida.",
            content="",
            sent_at=None,
            deleted_at=None,
            attachments=[],
            urls=[],
            metadata={
                "removed_channel_id": canal.id
            },
        )

        await interaction.response.send_message(
            f"✅ Regra LinkNot removida de "
            f"{canal.mention}.",
            ephemeral=True,
        )

    # ========================================================
    # /LINKNOT_ATIVAR
    # ========================================================

    @app_commands.command(
        name="linknot_ativar",
        description="Ativa o LinkNot de um canal."
    )
    @app_commands.describe(
        canal="Canal que terá a regra ativada."
    )
    @verificar_permissao()
    async def linknot_ativar(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel,
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                "❌ Use este comando dentro de um servidor.",
                ephemeral=True,
            )

            return

        try:

            config = obter_config(
                interaction.guild.id,
                canal.id
            )

            if not config:

                await interaction.response.send_message(
                    "❌ Este canal ainda não possui "
                    "uma regra LinkNot.",
                    ephemeral=True,
                )

                return

            (
                supabase
                .table("linknot_config")
                .update(
                    {
                        "enabled": True,
                        "updated_at": (
                            datetime.now(
                                timezone.utc
                            ).isoformat()
                        ),
                    }
                )
                .eq(
                    "guild_id",
                    interaction.guild.id
                )
                .eq(
                    "channel_id",
                    canal.id
                )
                .execute()
            )

        except Exception as erro:

            print(
                f"[LINKNOT] Erro ao ativar: {erro}",
                flush=True
            )

            await interaction.response.send_message(
                "❌ Não consegui ativar a regra.",
                ephemeral=True,
            )

            return

        registrar_log(
            guild_id=interaction.guild.id,
            channel_id=canal.id,
            user_id=interaction.user.id,
            message_id=0,
            username=str(interaction.user),
            display_name=interaction.user.display_name,
            action="linknot_enabled",
            reason="Regra LinkNot ativada.",
            content="",
            sent_at=None,
            deleted_at=None,
            attachments=[],
            urls=[],
            metadata={
                "channel_id": canal.id
            },
        )

        await interaction.response.send_message(
            f"🟢 LinkNot ativado em {canal.mention}.",
            ephemeral=True,
        )

    # ========================================================
    # /LINKNOT_DESATIVAR
    # ========================================================

    @app_commands.command(
        name="linknot_desativar",
        description="Desativa o LinkNot de um canal."
    )
    @app_commands.describe(
        canal="Canal que terá a regra desativada."
    )
    @verificar_permissao()
    async def linknot_desativar(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel,
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                "❌ Use este comando dentro de um servidor.",
                ephemeral=True,
            )

            return

        try:

            config = obter_config(
                interaction.guild.id,
                canal.id
            )

            if not config:

                await interaction.response.send_message(
                    "❌ Este canal ainda não possui "
                    "uma regra LinkNot.",
                    ephemeral=True,
                )

                return

            (
                supabase
                .table("linknot_config")
                .update(
                    {
                        "enabled": False,
                        "updated_at": (
                            datetime.now(
                                timezone.utc
                            ).isoformat()
                        ),
                    }
                )
                .eq(
                    "guild_id",
                    interaction.guild.id
                )
                .eq(
                    "channel_id",
                    canal.id
                )
                .execute()
            )

        except Exception as erro:

            print(
                f"[LINKNOT] Erro ao desativar: {erro}",
                flush=True
            )

            await interaction.response.send_message(
                "❌ Não consegui desativar a regra.",
                ephemeral=True,
            )

            return

        registrar_log(
            guild_id=interaction.guild.id,
            channel_id=canal.id,
            user_id=interaction.user.id,
            message_id=0,
            username=str(interaction.user),
            display_name=interaction.user.display_name,
            action="linknot_disabled",
            reason="Regra LinkNot desativada.",
            content="",
            sent_at=None,
            deleted_at=None,
            attachments=[],
            urls=[],
            metadata={
                "channel_id": canal.id
            },
        )

        await interaction.response.send_message(
            f"🔴 LinkNot desativado em {canal.mention}.",
            ephemeral=True,
        )

    # ========================================================
    # ON MESSAGE
    # ========================================================

    @commands.Cog.listener()
    async def on_message(
        self,
        message: discord.Message
    ):

        if message.author.bot:
            return

        if message.guild is None:
            return

        try:

            config = obter_config(
                message.guild.id,
                message.channel.id
            )

        except Exception as erro:

            print(
                f"[LINKNOT] Erro consultando configuração: {erro}",
                flush=True
            )

            return

        if not config:
            return

        if not config.get(
            "enabled",
            True
        ):
            return

        urls = extrair_urls(
            message.content
        )

        if not urls:
            return

        categorias = config.get(
            "allowed_categories",
            []
        )

        permitida, categoria_bloqueada = (
            mensagem_permitida(
                urls,
                categorias
            )
        )

        if permitida:
            return

        sent_at = (
            message.created_at
            if message.created_at
            else discord.utils.utcnow()
        )

        attachments = coletar_anexos(
            message
        )

        categoria_nome = nome_categoria(
            categoria_bloqueada
        )

        permitidos_texto = ", ".join(
            nome_categoria(c)
            for c in categorias
        )

        reason = (
            f"Link de **{categoria_nome}** "
            f"não permitido. "
            f"Permitidos: {permitidos_texto}."
        )

        deleted_at = None

        # ====================================================
        # EXCLUIR
        # ====================================================

        if config.get(
            "delete_message",
            True
        ):

            try:

                await message.delete()

                deleted_at = (
                    discord.utils.utcnow()
                )

                print(
                    f"[LINKNOT] Mensagem removida | "
                    f"guild={message.guild.id} | "
                    f"channel={message.channel.id} | "
                    f"user={message.author} | "
                    f"categoria={categoria_bloqueada}",
                    flush=True,
                )

            except discord.NotFound:

                deleted_at = (
                    discord.utils.utcnow()
                )

            except discord.Forbidden as erro:

                print(
                    f"[LINKNOT] Sem permissão para excluir "
                    f"mensagem: {erro}",
                    flush=True
                )

                deleted_at = (
                    discord.utils.utcnow()
                )

            except Exception as erro:

                print(
                    f"[LINKNOT] Erro ao excluir mensagem: "
                    f"{erro}",
                    flush=True
                )

                deleted_at = (
                    discord.utils.utcnow()
                )

        else:

            deleted_at = (
                discord.utils.utcnow()
            )

        # ====================================================
        # AVISO
        # ====================================================

        warning = config.get(
            "warning_message"
        ) or (
            "❌ Você não pode enviar este tipo "
            "de link neste canal."
        )

        roles = montar_mencoes_roles(
            message.guild,
            config.get(
                "role_ids",
                []
            )
        )

        texto_aviso = warning

        if roles:

            texto_aviso += (
                f"\n\n👮 {roles}"
            )

        try:

            aviso = await message.channel.send(
                texto_aviso,
                allowed_mentions=discord.AllowedMentions(
                    roles=True
                ),
            )

            try:

                await aviso.delete(
                    delay=8
                )

            except Exception:
                pass

        except Exception as erro:

            print(
                f"[LINKNOT] Erro ao enviar aviso: "
                f"{erro}",
                flush=True
            )

        # ====================================================
        # SUPABASE
        # ====================================================

        registrar_log(
            guild_id=message.guild.id,
            channel_id=message.channel.id,
            user_id=message.author.id,
            message_id=message.id,
            username=str(message.author),
            display_name=message.author.display_name,
            action="message_deleted",
            reason=reason,
            content=message.content,
            sent_at=sent_at,
            deleted_at=deleted_at,
            attachments=attachments,
            urls=urls,
            metadata={
                "blocked_category": categoria_bloqueada,
                "allowed_categories": categorias,
                "delete_message": config.get(
                    "delete_message",
                    True
                ),
                "log_channel_id": config.get(
                    "log_channel_id"
                ),
            },
        )

        # ====================================================
        # DISCORD
        # ====================================================

        await enviar_log_discord(
            guild=message.guild,
            config=config,
            message=message,
            reason=reason,
            urls=urls,
            attachments=attachments,
            sent_at=sent_at,
            deleted_at=deleted_at,
        )


# ============================================================
# SETUP
# ============================================================

async def setup(
    bot: commands.Bot
):

    await bot.add_cog(
        LinkNot(bot)
    )

    print(
        "🔗 cogs.linknot carregado com sucesso.",
        flush=True
    )