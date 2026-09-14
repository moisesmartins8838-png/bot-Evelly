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

EXTENSOES_COMPACTADOS = {
    ".zip",
    ".rar"
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
        arquivo.content_type
        or "application/octet-stream"
    )


# ============================================================
# BOTÃO DE DOWNLOAD
# ============================================================

class BotaoDownload(discord.ui.Button):

    def __init__(
        self,
        numero,
        nome,
        url_original
    ):

        nome_botao = nome

        if len(nome_botao) > 65:
            nome_botao = (
                nome_botao[:62]
                + "..."
            )

        super().__init__(
            label=(
                f"⬇️ {numero} • "
                f"{nome_botao}"
            ),
            style=discord.ButtonStyle.secondary,
            custom_id=(
                f"evelly_download_"
                f"{uuid.uuid4().hex}"
            )
        )

        self.numero = numero
        self.nome_arquivo = nome
        self.url_original = url_original


    async def callback(
        self,
        interaction: discord.Interaction
    ):

        print(
            "==============================================",
            flush=True
        )

        print(
            "⬇️ DOWNLOAD SOLICITADO",
            flush=True
        )

        print(
            f"👤 Usuário: {interaction.user}",
            flush=True
        )

        print(
            f"📄 Arquivo: {self.nome_arquivo}",
            flush=True
        )

        print(
            "🔗 Usando URL original do Discord",
            flush=True
        )


        # ====================================================
        # RESPONDER AO CLIQUE
        # ====================================================

        try:

            await interaction.response.send_message(
                content=None,
                embed=discord.Embed(
                    title="⬇️ Download do arquivo",
                    description=(
                        f"📦 **{self.nome_arquivo}**\n\n"
                        "Clique no botão abaixo "
                        "para baixar o arquivo."
                    ),
                    color=discord.Color.dark_grey()
                ),
                view=DownloadOriginalView(
                    self.nome_arquivo,
                    self.url_original
                ),
                ephemeral=True
            )

            print(
                "✅ Link original enviado ao usuário!",
                flush=True
            )

        except discord.NotFound:

            print(
                "❌ Interação do botão expirou.",
                flush=True
            )

        except discord.HTTPException as e:

            print(
                "❌ ERRO HTTP AO ENVIAR DOWNLOAD",
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

        except Exception as e:

            print(
                "❌ ERRO AO ENVIAR DOWNLOAD",
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


# ============================================================
# VIEW — BOTÃO FINAL DO DOWNLOAD
# ============================================================

class DownloadOriginalView(
    discord.ui.View
):

    def __init__(
        self,
        nome,
        url
    ):

        super().__init__(
            timeout=300
        )

        botao = discord.ui.Button(
            label="⬇️ BAIXAR ARQUIVO",
            style=discord.ButtonStyle.link,
            url=url
        )

        self.add_item(
            botao
        )


# ============================================================
# VIEW DOS POSTS
# ============================================================

class DownloadView(
    discord.ui.View
):

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

            url_original = arquivo[
                "url_original"
            ]

            linha = (
                (numero - 1)
                // 5
            )

            botao = BotaoDownload(
                numero=numero,
                nome=nome,
                url_original=url_original
            )

            botao.row = linha

            self.add_item(
                botao
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
        # ACK DA INTERAÇÃO
        # ====================================================
        #
        # A bot.py atual da Evelly já faz o ACK antecipado
        # para /post.
        #
        # Portanto NÃO respondemos novamente aqui.
        #
        # ====================================================

        print(
            "✅ /post recebeu ACK antecipado.",
            flush=True
        )

        print(
            "🚀 Iniciando processamento...",
            flush=True
        )


        try:

            # =================================================
            # CLASSIFICAR ARQUIVOS
            # =================================================

            imagens = []
            videos = []
            compactados = []
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


                elif extensao in EXTENSOES_COMPACTADOS:

                    compactados.append(
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


            if compactados:

                tipos.append(
                    "📦 Compactado"
                )


            if outros:

                tipos.append(
                    "📄 Arquivo"
                )


            tipo_texto = (
                "\n".join(tipos)
                if tipos
                else
                "📦 Arquivo"
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


                # =================================================
                # URL ORIGINAL DO DISCORD
                # =================================================

                url_original = arquivo.url


                print(
                    "🔗 URL original do Discord capturada.",
                    flush=True
                )


                # =================================================
                # LER ARQUIVO
                # =================================================

                dados = await arquivo.read()


                print(
                    f"💾 Bytes lidos: {len(dados)}",
                    flush=True
                )


                # =================================================
                # CONTENT TYPE
                # =================================================

                content_type = (
                    pegar_content_type(
                        arquivo
                    )
                )


                print(
                    f"📌 Content-Type: {content_type}",
                    flush=True
                )


                # =================================================
                # NOME LIMPO
                # =================================================

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
                    f"📂 Caminho Supabase: {caminho}",
                    flush=True
                )


                # =================================================
                # UPLOAD PARA SUPABASE
                # =================================================

                print(
                    "☁️ Enviando para Supabase...",
                    flush=True
                )


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


                # =================================================
                # GUARDAR INFORMAÇÕES
                # =================================================

                arquivos_publicados.append(

                    {

                        "nome":
                            arquivo.filename,

                        "url_original":
                            url_original,

                        "tamanho":
                            arquivo.size,

                        "caminho":
                            caminho,

                        "content_type":
                            content_type

                    }

                )


                # =================================================
                # PRIMEIRA IMAGEM
                # =================================================
                #
                # Para a imagem do Embed continuamos usando
                # o arquivo armazenado no Supabase.
                #
                # O download, porém, usa o URL original.
                #
                # =================================================

                extensao = pegar_extensao(
                    arquivo.filename
                )


                if (

                    primeira_imagem_url
                    is None

                    and
                    extensao
                    in
                    EXTENSOES_IMAGEM

                ):

                    try:

                        public_url = (

                            supabase
                            .storage
                            .from_(BUCKET)
                            .get_public_url(
                                caminho
                            )

                        )

                        if isinstance(
                            public_url,
                            str
                        ):

                            primeira_imagem_url = (
                                public_url
                            )

                        elif hasattr(
                            public_url,
                            "public_url"
                        ):

                            primeira_imagem_url = (
                                public_url.public_url
                            )

                    except Exception:

                        print(
                            "⚠️ Não foi possível "
                            "obter URL pública "
                            "da imagem.",
                            flush=True
                        )


            # =================================================
            # QUANTIDADE
            # =================================================

            if quantidade == 1:

                quantidade_texto = (
                    "1 arquivo"
                )

            else:

                quantidade_texto = (
                    f"{quantidade} arquivos"
                )


            # =================================================
            # EMBED
            # =================================================

            embed = discord.Embed(

                title=titulo,

                description=(

                    "📥 **Download**\n\n"

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
            # CAMPOS PRINCIPAIS
            # =================================================

            embed.add_field(

                name="📦 Arquivos",

                value=(
                    quantidade_texto
                ),

                inline=True

            )


            embed.add_field(

                name="📌 Conteúdo",

                value=(
                    tipo_texto
                ),

                inline=True

            )


            embed.add_field(

                name="👤 Publicado por",

                value=(
                    interaction.user.mention
                ),

                inline=True

            )


            # =================================================
            # SOMENTE ZIP E RAR
            # =================================================

            if compactados:

                lista_compactados = []


                for arquivo in compactados:

                    nome = (
                        arquivo.filename
                    )


                    if len(nome) > 55:

                        nome = (
                            nome[:52]
                            + "..."
                        )


                    tamanho = (
                        formatar_tamanho(
                            arquivo.size
                        )
                    )


                    lista_compactados.append(

                        f"📦 **{nome}** "
                        f"• `{tamanho}`"

                    )


                embed.add_field(

                    name=(
                        "📦 Arquivos compactados"
                    ),

                    value=(
                        "\n".join(
                            lista_compactados
                        )
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
            # IMAGEM PRINCIPAL
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
            # VIEW DE DOWNLOAD
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
                "🔒 Armazenamento: Supabase",
                flush=True
            )

            print(
                "🔗 Download: URL ORIGINAL DO DISCORD",
                flush=True
            )


            mensagem = await interaction.channel.send(

                embed=embed,

                view=view

            )


            print(
                "✅ POST PUBLICADO!",
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
            # ATUALIZAR RESPOSTA EPHEMERAL
            # =================================================

            try:

                await interaction.edit_original_response(

                    content=(

                        "✅ **Post publicado "
                        "com sucesso!**\n\n"

                        f"📦 {quantidade_texto}\n"

                        "🔒 Arquivos armazenados "
                        "com segurança."

                    )

                )

            except Exception as e:

                print(

                    "⚠️ Não foi possível "
                    "atualizar a mensagem "
                    f"temporária: {e}",

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

                        "❌ **Erro ao publicar "
                        "o post.**\n"

                        "Verifique o terminal "
                        "da Evelly."

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
                "❌ ERRO NO PROCESSAMENTO "
                "DO /POST",
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

                        "❌ **Erro ao publicar "
                        "o post.**\n\n"

                        f"🔎 `{type(e).__name__}`\n\n"

                        "Veja o terminal da Evelly "
                        "para mais detalhes."

                    )

                )

            except Exception as erro_resposta:

                print(

                    "⚠️ Não foi possível "
                    "atualizar a resposta "
                    "temporária.",

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