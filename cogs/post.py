import os
import uuid
import traceback

import discord
from discord import app_commands
from discord.ext import commands

from dotenv import load_dotenv
from supabase import create_client


# ============================================================
# CONFIGURAÇÕES
# ============================================================

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY")

BUCKET = "post-files"

# Tempo dos links de download
# 7 dias = 604800 segundos
TEMPO_LINK = 604800


# ============================================================
# VALIDAR SUPABASE
# ============================================================

if not SUPABASE_URL:
    raise RuntimeError(
        "❌ SUPABASE_URL não foi encontrado no .env"
    )

if not SUPABASE_KEY:
    raise RuntimeError(
        "❌ SUPABASE_PUBLISHABLE_KEY não foi encontrado no .env"
    )


# ============================================================
# CLIENTE SUPABASE
# ============================================================

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


# ============================================================
# EXTENSÕES
# ============================================================

EXTENSOES_IMAGEM = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif"
}

EXTENSOES_VIDEO = {
    ".mp4",
    ".mov",
    ".webm",
    ".mkv"
}


# ============================================================
# FUNÇÃO — EXTENSÃO
# ============================================================

def pegar_extensao(nome):

    nome = nome.lower()

    if "." not in nome:
        return ""

    return "." + nome.rsplit(".", 1)[1]


# ============================================================
# FUNÇÃO — TAMANHO
# ============================================================

def formatar_tamanho(tamanho):

    if tamanho < 1024:

        return f"{tamanho} B"

    if tamanho < 1024 * 1024:

        return f"{tamanho / 1024:.1f} KB"

    if tamanho < 1024 * 1024 * 1024:

        return f"{tamanho / (1024 * 1024):.1f} MB"

    return (
        f"{tamanho / (1024 * 1024 * 1024):.1f} GB"
    )


# ============================================================
# FUNÇÃO — CONTENT TYPE
# ============================================================

def pegar_content_type(arquivo):

    extensao = pegar_extensao(
        arquivo.filename
    )

    tipos = {

        ".png": "image/png",

        ".jpg": "image/jpeg",

        ".jpeg": "image/jpeg",

        ".webp": "image/webp",

        ".gif": "image/gif",

        ".mp4": "video/mp4",

        ".mov": "video/quicktime",

        ".webm": "video/webm",

        ".mkv": "video/x-matroska",

        ".rar": "application/vnd.rar",

        ".zip": "application/zip",

        ".7z": "application/x-7z-compressed",

        ".pdf": "application/pdf",

        ".txt": "text/plain",

        ".json": "application/json",

        ".lua": "text/plain",

        ".luac": "application/octet-stream"
    }

    return tipos.get(
        extensao,
        arquivo.content_type or
        "application/octet-stream"
    )


# ============================================================
# FUNÇÃO — URL ASSINADA
# ============================================================

def criar_link_download(caminho):

    resultado = (
        supabase
        .storage
        .from_(BUCKET)
        .create_signed_url(
            caminho,
            TEMPO_LINK
        )
    )

    # --------------------------------------------------------
    # Supabase pode retornar formatos diferentes dependendo
    # da versão da biblioteca.
    # --------------------------------------------------------

    if isinstance(resultado, dict):

        url = (
            resultado.get("signedURL")
            or
            resultado.get("signed_url")
        )

        if url:
            return url

    # --------------------------------------------------------
    # Alguns retornos podem possuir atributo signed_url
    # --------------------------------------------------------

    if hasattr(
        resultado,
        "signed_url"
    ):

        return resultado.signed_url

    if hasattr(
        resultado,
        "signedURL"
    ):

        return resultado.signedURL

    raise RuntimeError(
        f"❌ Supabase não retornou uma URL assinada: "
        f"{resultado}"
    )


# ============================================================
# VIEW DOS DOWNLOADS
# ============================================================

class DownloadView(discord.ui.View):

    def __init__(
        self,
        arquivos
    ):

        super().__init__(
            timeout=None
        )

        for numero, arquivo in enumerate(
            arquivos,
            start=1
        ):

            nome = arquivo["nome"]

            url = arquivo["url"]

            # ------------------------------------------------
            # Limitar nome
            # ------------------------------------------------

            if len(nome) > 65:

                nome = (
                    nome[:62]
                    + "..."
                )

            # ------------------------------------------------
            # Discord permite no máximo 5 componentes
            # por linha.
            # ------------------------------------------------

            linha = (
                (numero - 1)
                // 5
            )

            self.add_item(

                discord.ui.Button(

                    label=(
                        f"⬇️ {numero} • {nome}"
                    ),

                    style=(
                        discord.ButtonStyle.link
                    ),

                    url=url,

                    row=linha
                )
            )


# ============================================================
# COG POST
# ============================================================

class Post(commands.Cog):

    def __init__(
        self,
        bot: commands.Bot
    ):

        self.bot = bot

    # ========================================================
    # /POST
    # ========================================================

    @app_commands.command(
        name="post",
        description=(
            "Publica até 10 arquivos "
            "em um Embed."
        )
    )
    @app_commands.default_permissions(
        administrator=True
    )
    @app_commands.describe(

        titulo=(
            "Título da publicação"
        ),

        arquivo1=(
            "Primeiro arquivo "
            "(obrigatório)"
        ),

        arquivo2=(
            "Segundo arquivo"
        ),

        arquivo3=(
            "Terceiro arquivo"
        ),

        arquivo4=(
            "Quarto arquivo"
        ),

        arquivo5=(
            "Quinto arquivo"
        ),

        arquivo6=(
            "Sexto arquivo"
        ),

        arquivo7=(
            "Sétimo arquivo"
        ),

        arquivo8=(
            "Oitavo arquivo"
        ),

        arquivo9=(
            "Nono arquivo"
        ),

        arquivo10=(
            "Décimo arquivo"
        )
    )
    async def post(

        self,

        interaction: discord.Interaction,

        titulo: str,

        arquivo1: discord.Attachment,

        arquivo2: discord.Attachment = None,

        arquivo3: discord.Attachment = None,

        arquivo4: discord.Attachment = None,

        arquivo5: discord.Attachment = None,

        arquivo6: discord.Attachment = None,

        arquivo7: discord.Attachment = None,

        arquivo8: discord.Attachment = None,

        arquivo9: discord.Attachment = None,

        arquivo10: discord.Attachment = None

    ):

        print(
            "==============================================",
            flush=True
        )

        print(
            "📦 /POST RECEBIDO",
            flush=True
        )

        print(
            f"👤 Usuário: {interaction.user}",
            flush=True
        )

        print(
            f"📝 Título: {titulo}",
            flush=True
        )

        # ====================================================
        # LISTA DOS ARQUIVOS
        # ====================================================

        arquivos = [

            arquivo1,

            arquivo2,

            arquivo3,

            arquivo4,

            arquivo5,

            arquivo6,

            arquivo7,

            arquivo8,

            arquivo9,

            arquivo10
        ]

        arquivos = [

            arquivo

            for arquivo in arquivos

            if arquivo is not None
        ]

        quantidade = len(
            arquivos
        )

        print(
            f"📁 Quantidade: {quantidade}",
            flush=True
        )

        # ====================================================
        # RESPOSTA IMEDIATA
        # ====================================================
        #
        # NÃO usamos defer().
        #
        # A Evelly responde imediatamente ao Discord.
        #
        # Depois disso podemos trabalhar no Supabase.
        #
        # ====================================================

        try:

            await interaction.response.send_message(

                "⏳ **Preparando publicação...**\n"
                "☁️ Enviando arquivos para o armazenamento...",

                ephemeral=True

            )

            print(
                "✅ Interação respondida imediatamente.",
                flush=True
            )

        except discord.NotFound as e:

            print(
                "==============================================",
                flush=True
            )

            print(
                "❌ UNKNOWN INTERACTION",
                flush=True
            )

            print(
                "O Discord considerou a interação expirada.",
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

        except Exception as e:

            print(
                "==============================================",
                flush=True
            )

            print(
                "❌ ERRO AO RESPONDER AO DISCORD",
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

            return

        # ====================================================
        # PROCESSAMENTO
        # ====================================================

        try:

            # =================================================
            # CLASSIFICAR
            # =================================================

            imagens = []

            videos = []

            outros = []

            for arquivo in arquivos:

                extensao = pegar_extensao(
                    arquivo.filename
                )

                if extensao in EXTENSOES_IMAGEM:

                    imagens.append(
                        arquivo
                    )

                elif extensao in EXTENSOES_VIDEO:

                    videos.append(
                        arquivo
                    )

                else:

                    outros.append(
                        arquivo
                    )

            # =================================================
            # TIPOS
            # =================================================

            tipos = []

            if imagens:

                tipos.append(
                    "🖼️ Imagem"
                )

            if videos:

                tipos.append(
                    "🎬 Vídeo"
                )

            if outros:

                tipos.append(
                    "📦 Arquivo"
                )

            tipo_texto = "\n".join(
                tipos
            )

            # =================================================
            # UPLOAD DOS ARQUIVOS
            # =================================================

            arquivos_publicados = []

            primeira_imagem_url = None

            for numero, arquivo in enumerate(
                arquivos,
                start=1
            ):

                print(
                    "----------------------------------------------",
                    flush=True
                )

                print(
                    f"☁️ UPLOAD {numero}/{quantidade}",
                    flush=True
                )

                print(
                    f"📄 Arquivo: {arquivo.filename}",
                    flush=True
                )

                print(
                    f"📦 Tamanho: "
                    f"{formatar_tamanho(arquivo.size)}",
                    flush=True
                )

                # --------------------------------------------
                # LER ARQUIVO
                # --------------------------------------------

                dados = await arquivo.read()

                print(
                    f"💾 Bytes lidos: {len(dados)}",
                    flush=True
                )

                # --------------------------------------------
                # CONTENT TYPE
                # --------------------------------------------

                content_type = (
                    pegar_content_type(
                        arquivo
                    )
                )

                print(
                    f"📌 Content-Type: {content_type}",
                    flush=True
                )

                # --------------------------------------------
                # NOME ÚNICO
                # --------------------------------------------

                nome_limpo = (
                    arquivo.filename
                    .replace(
                        "/",
                        "_"
                    )
                    .replace(
                        "\\",
                        "_"
                    )
                )

                identificador = (
                    uuid.uuid4().hex
                )

                guild_id = (
                    interaction.guild.id
                    if interaction.guild
                    else 0
                )

                caminho = (

                    f"{guild_id}/"

                    f"{identificador}_"

                    f"{nome_limpo}"
                )

                print(
                    f"📂 Caminho: {caminho}",
                    flush=True
                )

                # --------------------------------------------
                # ENVIAR AO SUPABASE
                # --------------------------------------------

                resultado_upload = (

                    supabase

                    .storage

                    .from_(BUCKET)

                    .upload(

                        caminho,

                        dados,

                        {
                            "content-type":
                                content_type,

                            "upsert":
                                "false"
                        }

                    )
                )

                print(
                    f"☁️ Resultado upload: "
                    f"{resultado_upload}",
                    flush=True
                )

                print(
                    "✅ Upload concluído!",
                    flush=True
                )

                # --------------------------------------------
                # CRIAR URL ASSINADA
                # --------------------------------------------

                print(
                    "🔐 Criando link privado...",
                    flush=True
                )

                url = criar_link_download(
                    caminho
                )

                print(
                    "✅ Link privado criado!",
                    flush=True
                )

                # --------------------------------------------
                # GUARDAR INFORMAÇÕES
                # --------------------------------------------

                arquivos_publicados.append(

                    {

                        "nome":
                            arquivo.filename,

                        "url":
                            url,

                        "tamanho":
                            arquivo.size,

                        "caminho":
                            caminho,

                        "content_type":
                            content_type
                    }
                )

                # --------------------------------------------
                # PRIMEIRA IMAGEM
                # --------------------------------------------

                extensao = pegar_extensao(
                    arquivo.filename
                )

                if (

                    primeira_imagem_url is None

                    and extensao in EXTENSOES_IMAGEM

                ):

                    primeira_imagem_url = url

            # =================================================
            # EMBED
            # =================================================

            if quantidade == 1:

                quantidade_texto = (
                    "1 arquivo"
                )

            else:

                quantidade_texto = (
                    f"{quantidade} arquivos"
                )

            embed = discord.Embed(

                title=titulo,

                description=(

                    "📥 **Download**\n"

                    "Use os botões abaixo "
                    "para baixar os arquivos."

                ),

                color=discord.Color.dark_grey()

            )

            # =================================================
            # AUTOR
            # =================================================

            if interaction.guild:

                embed.set_author(

                    name=(
                        interaction.guild.name
                    )

                )

            # =================================================
            # CAMPOS
            # =================================================

            embed.add_field(

                name="📦 Arquivos",

                value=quantidade_texto,

                inline=True

            )

            embed.add_field(

                name="📌 Conteúdo",

                value=tipo_texto,

                inline=True

            )

            embed.add_field(

                name="👤 Publicado por",

                value=interaction.user.mention,

                inline=True

            )

            # =================================================
            # LISTA
            # =================================================

            lista = []

            for numero, arquivo in enumerate(

                arquivos_publicados,

                start=1

            ):

                nome = arquivo["nome"]

                if len(nome) > 55:

                    nome = (
                        nome[:52]
                        + "..."
                    )

                tamanho = (
                    formatar_tamanho(
                        arquivo["tamanho"]
                    )
                )

                lista.append(

                    f"`{numero}.` "
                    f"**{nome}** "
                    f"• `{tamanho}`"

                )

            embed.add_field(

                name="📂 Arquivos disponíveis",

                value="\n".join(
                    lista
                ),

                inline=False

            )

            # =================================================
            # THUMBNAIL
            # =================================================

            if interaction.guild:

                if interaction.guild.icon:

                    embed.set_thumbnail(

                        url=(
                            interaction.guild
                            .icon
                            .url
                        )

                    )

            # =================================================
            # IMAGEM
            # =================================================

            if primeira_imagem_url:

                embed.set_image(

                    url=(
                        primeira_imagem_url
                    )

                )

            # =================================================
            # FOOTER
            # =================================================

            embed.set_footer(

                text=(
                    "© Evelly LN • "
                    "Todos os direitos reservados"
                )

            )

            # =================================================
            # VIEW
            # =================================================

            view = DownloadView(

                arquivos_publicados

            )

            # =================================================
            # PUBLICAR POST
            # =================================================

            print(
                "==============================================",
                flush=True
            )

            print(
                "📤 PUBLICANDO POST FINAL",
                flush=True
            )

            print(
                "📎 Anexos Discord: 0",
                flush=True
            )

            print(
                "🔒 Arquivos: Supabase privado",
                flush=True
            )

            # -------------------------------------------------
            # IMPORTANTE:
            #
            # Não usamos files=.
            #
            # Portanto o Discord não mostrará:
            #
            # 📎 triadb.rar
            #
            # acima do Embed.
            # -------------------------------------------------

            mensagem = await interaction.channel.send(

                embed=embed,

                view=view

            )

            print(
                f"✅ POST PUBLICADO!",
                flush=True
            )

            print(
                f"🆔 ID: {mensagem.id}",
                flush=True
            )

            # =================================================
            # REAÇÕES
            # =================================================

            print(
                "👍 Adicionando reações...",
                flush=True
            )

            await mensagem.add_reaction(
                "✅"
            )

            await mensagem.add_reaction(
                "❌"
            )

            print(
                "✅ Reações adicionadas!",
                flush=True
            )

            # =================================================
            # ATUALIZAR MENSAGEM EPHEMERAL
            # =================================================

            try:

                await interaction.edit_original_response(

                    content=(
                        "✅ **Post publicado com sucesso!**\n"
                        f"📦 {quantidade_texto}\n"
                        "🔒 Arquivos armazenados com "
                        "segurança no Supabase."
                    )

                )

            except Exception as e:

                print(
                    f"⚠️ Não foi possível atualizar "
                    f"a mensagem temporária: {e}",
                    flush=True
                )

            print(
                "==============================================",
                flush=True
            )

            print(
                "🎉 POST CONCLUÍDO COM SUCESSO!",
                flush=True
            )

            print(
                "==============================================",
                flush=True
            )

        # ====================================================
        # ERRO HTTP DISCORD
        # ====================================================

        except discord.HTTPException as e:

            print(
                "==============================================",
                flush=True
            )

            print(
                "❌ ERRO HTTP NO POST",
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

            traceback.print_exc()

            print(
                "==============================================",
                flush=True
            )

            try:

                await interaction.edit_original_response(

                    content=(
                        "❌ **Erro ao publicar o post.**\n"
                        "Verifique o terminal da Evelly."
                    )

                )

            except Exception:

                pass

        # ====================================================
        # ERRO SUPABASE / GERAL
        # ====================================================

        except Exception as e:

            print(
                "==============================================",
                flush=True
            )

            print(
                "❌ ERRO NO PROCESSAMENTO DO /POST",
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

            print(
                "📜 TRACEBACK:",
                flush=True
            )

            traceback.print_exc()

            print(
                "==============================================",
                flush=True
            )

            try:

                await interaction.edit_original_response(

                    content=(
                        "❌ **Erro ao publicar o post.**\n\n"
                        f"🔎 `{type(e).__name__}`\n"
                        "Veja o terminal da Evelly "
                        "para mais detalhes."
                    )

                )

            except Exception as erro_resposta:

                print(
                    "⚠️ Não foi possível atualizar "
                    "a resposta temporária.",
                    flush=True
                )

                print(
                    f"Erro: {erro_resposta}",
                    flush=True
                )


# ============================================================
# SETUP
# ============================================================

async def setup(
    bot: commands.Bot
):

    await bot.add_cog(
        Post(bot)
    )

    print(
        "✅ Sistema /post carregado!",
        flush=True
    )