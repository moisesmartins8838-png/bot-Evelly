import asyncio
import re
from datetime import datetime

import aiohttp
import discord

from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import View, Button

from database.database import (
    criar_servidor,
    pegar_servidor,
    adicionar_youtube,
    remover_youtube,
    listar_youtube,
    pegar_todos_youtube,
    atualizar_ultimo_video
)


# =========================================================
# CONFIGURAÇÕES
# =========================================================

YOUTUBE_API = "https://www.googleapis.com/youtube/v3"

# Intervalo de verificação
INTERVALO_VERIFICACAO = 2


# =========================================================
# BOTÃO DO VÍDEO
# =========================================================

class YouTubeView(View):

    def __init__(self, video_url, canal_url):

        super().__init__(
            timeout=None
        )

        # -------------------------------------------------
        # BOTÃO ASSISTIR
        # -------------------------------------------------

        self.add_item(
            Button(
                label="Assistir vídeo",
                emoji="▶️",
                style=discord.ButtonStyle.link,
                url=video_url
            )
        )

        # -------------------------------------------------
        # BOTÃO CANAL
        # -------------------------------------------------

        self.add_item(
            Button(
                label="Ver canal",
                emoji="📺",
                style=discord.ButtonStyle.link,
                url=canal_url
            )
        )


# =========================================================
# YOUTUBE
# =========================================================

class YouTube(commands.Cog):

    youtube = app_commands.Group(
        name="youtube",
        description="Sistema de notificações do YouTube."
    )


    # =====================================================
    # INICIALIZAÇÃO
    # =====================================================

    def __init__(self, bot):

        self.bot = bot
        self.api_key = bot.youtube_api_key

        print(
            "🎬 Sistema YouTube iniciado.",
            flush=True
        )

        self.monitorar.start()


    # =====================================================
    # FINALIZAÇÃO
    # =====================================================

    def cog_unload():

        self.monitorar.cancel()


    # =====================================================
    # REQUISIÇÃO À API
    # =====================================================

    async def api_request(
        self,
        endpoint,
        params
    ):

        params["key"] = self.api_key

        try:

            async with aiohttp.ClientSession() as session:

                async with session.get(
                    f"{YOUTUBE_API}/{endpoint}",
                    params=params,
                    timeout=20
                ) as response:

                    if response.status != 200:

                        texto = await response.text()

                        print(
                            "❌ Erro na API do YouTube:",
                            flush=True
                        )

                        print(
                            texto,
                            flush=True
                        )

                        return None

                    return await response.json()

        except asyncio.TimeoutError:

            print(
                "❌ Tempo limite excedido ao acessar o YouTube.",
                flush=True
            )

            return None

        except Exception as erro:

            print(
                f"❌ Erro ao acessar YouTube: {erro}",
                flush=True
            )

            return None


    # =====================================================
    # OBTER CANAL
    # =====================================================

    async def obter_canal(
        self,
        url
    ):

        url = url.strip()


        # -------------------------------------------------
        # CHANNEL ID
        # -------------------------------------------------

        match = re.search(
            r"(UC[a-zA-Z0-9_-]{20,})",
            url
        )

        if match:

            channel_id = match.group(1)

            dados = await self.api_request(
                "channels",
                {
                    "part": "snippet,contentDetails",
                    "id": channel_id
                }
            )

            if dados and dados.get("items"):

                return dados["items"][0]

            return None


        # -------------------------------------------------
        # HANDLE @CANAL
        # -------------------------------------------------

        match = re.search(
            r"/@([a-zA-Z0-9._-]+)",
            url
        )

        if match:

            handle = match.group(1)

            dados = await self.api_request(
                "channels",
                {
                    "part": "snippet,contentDetails",
                    "forHandle": handle
                }
            )

            if dados and dados.get("items"):

                return dados["items"][0]

            return None


        return None


    # =====================================================
    # OBTER ÚLTIMO VÍDEO
    # =====================================================

    async def obter_ultimo_video(
        self,
        uploads_playlist
    ):

        dados = await self.api_request(
            "playlistItems",
            {
                "part": "snippet,contentDetails",
                "playlistId": uploads_playlist,
                "maxResults": 1
            }
        )

        if not dados:

            return None


        itens = dados.get(
            "items",
            []
        )

        if not itens:

            return None


        item = itens[0]

        video_id = (
            item
            .get("contentDetails", {})
            .get("videoId")
        )


        return video_id


    # =====================================================
    # OBTER INFORMAÇÕES COMPLETAS DO VÍDEO
    # =====================================================

    async def obter_video(
        self,
        video_id
    ):

        dados = await self.api_request(
            "videos",
            {
                "part": "snippet,contentDetails",
                "id": video_id
            }
        )

        if not dados:

            return None


        itens = dados.get(
            "items",
            []
        )

        if not itens:

            return None


        video = itens[0]

        snippet = video.get(
            "snippet",
            {}
        )


        # -------------------------------------------------
        # TÍTULO
        # -------------------------------------------------

        titulo = snippet.get(
            "title",
            "Novo vídeo"
        )


        # -------------------------------------------------
        # DESCRIÇÃO
        # -------------------------------------------------

        descricao = snippet.get(
            "description",
            ""
        )


        # -------------------------------------------------
        # DATA
        # -------------------------------------------------

        publicado_em = snippet.get(
            "publishedAt"
        )


        # -------------------------------------------------
        # THUMBNAILS
        # -------------------------------------------------

        thumbnails = snippet.get(
            "thumbnails",
            {}
        )


        thumbnail = None


        # Preferência:
        # maxres > standard > high > medium > default

        for tamanho in [
            "maxres",
            "standard",
            "high",
            "medium",
            "default"
        ]:

            if tamanho in thumbnails:

                thumbnail = thumbnails[
                    tamanho
                ].get("url")

                if thumbnail:
                    break


        return {
            "titulo": titulo,
            "descricao": descricao,
            "publicado_em": publicado_em,
            "thumbnail": thumbnail
        }


    # =====================================================
    # /YOUTUBE ADICIONAR
    # =====================================================

    @youtube.command(
        name="adicionar",
        description="Adiciona um canal do YouTube para monitoramento."
    )

    @app_commands.describe(
        canal="Link do canal do YouTube."
    )

    async def adicionar(
        self,
        interaction: discord.Interaction,
        canal: str
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                "❌ Este comando só pode ser usado em um servidor.",
                ephemeral=True
            )

            return


        await interaction.response.defer()


        guild_id = interaction.guild.id


        # -------------------------------------------------
        # BUSCAR CANAL
        # -------------------------------------------------

        canal_info = await self.obter_canal(
            canal
        )


        if not canal_info:

            await interaction.followup.send(
                "❌ Não consegui encontrar esse canal do YouTube.\n\n"
                "Use um link como:\n"
                "`https://www.youtube.com/@Canal`\n\n"
                "ou:\n"
                "`https://www.youtube.com/channel/UC...`"
            )

            return


        # -------------------------------------------------
        # INFORMAÇÕES
        # -------------------------------------------------

        youtube_id = canal_info["id"]

        nome = canal_info[
            "snippet"
        ]["title"]

        uploads_playlist = (
            canal_info
            ["contentDetails"]
            ["relatedPlaylists"]
            ["uploads"]
        )


        # -------------------------------------------------
        # ÚLTIMO VÍDEO
        # -------------------------------------------------

        ultimo_video = await self.obter_ultimo_video(
            uploads_playlist
        )


        # -------------------------------------------------
        # SALVAR
        # -------------------------------------------------

        resultado = adicionar_youtube(

            guild_id=guild_id,

            youtube_id=youtube_id,

            nome=nome,

            uploads_playlist=uploads_playlist,

            ultimo_video=ultimo_video
        )


        if resultado is None:

            await interaction.followup.send(
                "❌ Não consegui salvar o canal no banco de dados."
            )

            return


        # -------------------------------------------------
        # URL DO CANAL
        # -------------------------------------------------

        canal_url = (
            f"https://www.youtube.com/channel/"
            f"{youtube_id}"
        )


        # -------------------------------------------------
        # EMBED
        # -------------------------------------------------

        embed = discord.Embed(

            title="📺 Canal adicionado!",

            description=(
                f"A Evelly começou a monitorar "
                f"**{nome}**."
            ),

            color=discord.Color.green()
        )


        embed.add_field(
            name="📺 Canal",
            value=f"[{nome}]({canal_url})",
            inline=False
        )


        embed.add_field(
            name="🔔 Monitoramento",
            value=(
                "🟢 Ativo\n"
                "A Evelly verificará automaticamente "
                "novos vídeos."
            ),
            inline=False
        )


        embed.set_thumbnail(
            url=(
                canal_info
                ["snippet"]
                ["thumbnails"]
                .get("high",
                     canal_info
                     ["snippet"]
                     ["thumbnails"]
                     .get("default"))
                ["url"]
            )
        )


        embed.set_footer(
            text="Evelly LN • YouTube Notifications"
        )


        await interaction.followup.send(
            embed=embed
        )


    # =====================================================
    # /YOUTUBE REMOVER
    # =====================================================

    @youtube.command(
        name="remover",
        description="Remove um canal do monitoramento."
    )

    @app_commands.describe(
        canal_id="ID do canal do YouTube."
    )

    async def remover(
        self,
        interaction: discord.Interaction,
        canal_id: str
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                "❌ Este comando só pode ser usado em um servidor.",
                ephemeral=True
            )

            return


        removido = remover_youtube(

            interaction.guild.id,

            canal_id
        )


        if removido:

            await interaction.response.send_message(
                "✅ Canal removido do monitoramento."
            )

        else:

            await interaction.response.send_message(
                "❌ Não encontrei esse canal na lista."
            )


    # =====================================================
    # /YOUTUBE LISTAR
    # =====================================================

    @youtube.command(
        name="listar",
        description="Lista os canais monitorados."
    )

    async def listar(
        self,
        interaction: discord.Interaction
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                "❌ Este comando só pode ser usado em um servidor.",
                ephemeral=True
            )

            return


        canais = listar_youtube(
            interaction.guild.id
        )


        if not canais:

            await interaction.response.send_message(
                "📺 Nenhum canal do YouTube "
                "está sendo monitorado."
            )

            return


        embed = discord.Embed(

            title="📺 Canais monitorados",

            description=(
                "Confira abaixo os canais "
                "atualmente monitorados pela Evelly."
            ),

            color=discord.Color.red()
        )


        texto = ""


        for (
            youtube_id,
            nome,
            ultimo_video,
            ativo
        ) in canais:

            status = (
                "🟢"
                if ativo
                else
                "🔴"
            )


            texto += (
                f"{status} **{nome}**\n"
                f"🆔 `{youtube_id}`\n\n"
            )


        if len(texto) > 4000:

            texto = (
                texto[:3997]
                + "..."
            )


        embed.add_field(
            name="Canais",
            value=texto,
            inline=False
        )


        embed.set_footer(
            text=(
                f"Evelly LN • "
                f"{len(canais)} canal(is) monitorado(s)"
            )
        )


        await interaction.response.send_message(
            embed=embed
        )


    # =====================================================
    # /YOUTUBE STATUS
    # =====================================================

    @youtube.command(
        name="status",
        description="Mostra o status do sistema YouTube."
    )

    async def status(
        self,
        interaction: discord.Interaction
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                "❌ Este comando só pode ser usado em um servidor.",
                ephemeral=True
            )

            return


        criar_servidor(
            interaction.guild.id
        )


        servidor = pegar_servidor(
            interaction.guild.id
        )


        canais = listar_youtube(
            interaction.guild.id
        )


        if not servidor:

            await interaction.response.send_message(
                "❌ Não consegui carregar as configurações.",
                ephemeral=True
            )

            return


        canal_discord = servidor[1]


        embed = discord.Embed(

            title="🎬 Sistema YouTube",

            description=(
                "Status atual do sistema "
                "de notificações."
            ),

            color=discord.Color.green()
        )


        embed.add_field(
            name="📺 Canais monitorados",
            value=str(len(canais)),
            inline=True
        )


        embed.add_field(
            name="📢 Canal de anúncios",
            value=(
                f"<#{canal_discord}>"
                if canal_discord
                else "❌ Não configurado"
            ),
            inline=True
        )


        embed.add_field(
            name="🤖 Monitoramento",
            value="🟢 Online",
            inline=False
        )


        embed.add_field(
            name="⏱️ Verificação",
            value=(
                f"A cada {INTERVALO_VERIFICACAO} minutos"
            ),
            inline=False
        )


        embed.set_footer(
            text="Evelly LN • YouTube System"
        )


        await interaction.response.send_message(
            embed=embed
        )


    # =====================================================
    # MONITORAMENTO
    # =====================================================

    @tasks.loop(
        minutes=INTERVALO_VERIFICACAO
    )

    async def monitorar(self):

        await self.bot.wait_until_ready()


        registros = pegar_todos_youtube()


        if not registros:

            return


        print(
            f"📺 Verificando "
            f"{len(registros)} canal(is) "
            f"do YouTube...",
            flush=True
        )


        for registro in registros:

            (
                registro_id,
                guild_id,
                youtube_id,
                nome,
                uploads_playlist,
                ultimo_video,
                ativo
            ) = registro


            try:

                # -----------------------------------------
                # BUSCAR VÍDEO MAIS RECENTE
                # -----------------------------------------

                novo_video = await self.obter_ultimo_video(
                    uploads_playlist
                )


                if not novo_video:

                    continue


                # -----------------------------------------
                # PRIMEIRO VÍDEO
                # -----------------------------------------

                if not ultimo_video:

                    atualizar_ultimo_video(

                        registro_id,

                        novo_video
                    )

                    continue


                # -----------------------------------------
                # MESMO VÍDEO
                # -----------------------------------------

                if novo_video == ultimo_video:

                    continue


                # -----------------------------------------
                # NOVO VÍDEO
                # -----------------------------------------

                print(
                    f"🆕 Novo vídeo encontrado: "
                    f"{nome}",
                    flush=True
                )


                atualizar_ultimo_video(

                    registro_id,

                    novo_video
                )


                await self.anunciar_video(

                    guild_id,

                    youtube_id,

                    nome,

                    novo_video
                )


                await asyncio.sleep(
                    1
                )


            except Exception as erro:

                print(
                    f"❌ Erro monitorando "
                    f"{nome}: {erro}",
                    flush=True
                )


    # =====================================================
    # ANTES DO MONITORAMENTO
    # =====================================================

    @monitorar.before_loop
    async def antes_monitorar(self):

        await self.bot.wait_until_ready()


    # =====================================================
    # ANUNCIAR VÍDEO
    # =====================================================

    async def anunciar_video(

        self,

        guild_id,

        youtube_id,

        nome,

        video_id

    ):

        # =================================================
        # SERVIDOR
        # =================================================

        guild = self.bot.get_guild(
            guild_id
        )


        if guild is None:

            print(
                f"⚠️ Servidor {guild_id} "
                "não está disponível.",
                flush=True
            )

            return


        # =================================================
        # CONFIGURAÇÕES
        # =================================================

        servidor = pegar_servidor(
            guild_id
        )


        if not servidor:

            return


        canal_id = servidor[1]

        cargo_id = servidor[2]

        mensagem_personalizada = servidor[3]


        # =================================================
        # CANAL
        # =================================================

        if not canal_id:

            print(
                f"⚠️ Servidor {guild_id} "
                "não possui canal de anúncios.",
                flush=True
            )

            return


        canal_discord = guild.get_channel(
            canal_id
        )


        if canal_discord is None:

            print(
                f"⚠️ Canal {canal_id} "
                "não encontrado.",
                flush=True
            )

            return


        # =================================================
        # LINKS
        # =================================================

        video_url = (
            f"https://www.youtube.com/watch?v="
            f"{video_id}"
        )


        canal_url = (
            f"https://www.youtube.com/channel/"
            f"{youtube_id}"
        )


        # =================================================
        # INFORMAÇÕES DO VÍDEO
        # =================================================

        video_info = await self.obter_video(
            video_id
        )


        # =================================================
        # DADOS PADRÃO
        # =================================================

        titulo = "Novo vídeo"

        descricao = ""

        thumbnail = None

        publicado_em = None


        # =================================================
        # APLICAR DADOS DO YOUTUBE
        # =================================================

        if video_info:

            titulo = video_info.get(
                "titulo",
                titulo
            )

            descricao = video_info.get(
                "descricao",
                ""
            )

            thumbnail = video_info.get(
                "thumbnail"
            )

            publicado_em = video_info.get(
                "publicado_em"
            )


        # =================================================
        # LIMPAR DESCRIÇÃO
        # =================================================

        if descricao:

            descricao = descricao.strip()


            if len(descricao) > 300:

                descricao = (
                    descricao[:297]
                    + "..."
                )


        if not descricao:

            descricao = (
                "Um novo conteúdo acaba "
                "de ser publicado."
            )


        # =================================================
        # CARGO
        # =================================================

        mencao = ""


        if cargo_id:

            cargo = guild.get_role(
                cargo_id
            )


            if cargo:

                mencao = cargo.mention


        # =================================================
        # MENSAGEM PERSONALIZADA
        # =================================================

        if mensagem_personalizada:

            texto = mensagem_personalizada


            texto = texto.replace(
                "{canal}",
                nome
            )


            texto = texto.replace(
                "{video}",
                video_url
            )


            texto = texto.replace(
                "{video_id}",
                video_id
            )


            texto = texto.replace(
                "{titulo}",
                titulo
            )


        else:

            texto = (
                "🚨 **Saiu vídeo novo!**"
            )


        # =================================================
        # EMBED
        # =================================================

        embed = discord.Embed(

            title=f"🎬 {titulo}",

            description=(
                f"📺 **{nome}**\n"
                f"acabou de publicar um novo vídeo!\n\n"
                f"📝 {descricao}"
            ),

            color=discord.Color.from_rgb(
                255,
                0,
                0
            ),

            url=video_url
        )


        # =================================================
        # AUTOR DO EMBED
        # =================================================

        embed.set_author(

            name=f"🔴 {nome}",

            url=canal_url
        )


        # =================================================
        # THUMBNAIL
        # =================================================

        if thumbnail:

            embed.set_image(
                url=thumbnail
            )


        # =================================================
        # INFORMAÇÕES
        # =================================================

        embed.add_field(

            name="📺 Canal",

            value=(
                f"[{nome}]({canal_url})"
            ),

            inline=True
        )


        embed.add_field(

            name="▶️ Vídeo",

            value=(
                "[Assistir no YouTube]"
                f"({video_url})"
            ),

            inline=True
        )


        # =================================================
        # DATA
        # =================================================

        if publicado_em:

            try:

                data_publicacao = (
                    datetime
                    .fromisoformat(
                        publicado_em
                        .replace(
                            "Z",
                            "+00:00"
                        )
                    )
                )


                embed.add_field(

                    name="📅 Publicado",

                    value=discord.utils.format_dt(
                        data_publicacao,
                        style="R"
                    ),

                    inline=True
                )


                embed.timestamp = (
                    data_publicacao
                )


            except Exception:

                pass


        # =================================================
        # FOOTER
        # =================================================

        embed.set_footer(

            text=(
                "Evelly LN • "
                "YouTube Notifications"
            )
        )


        # =================================================
        # BOTÕES
        # =================================================

        view = YouTubeView(

            video_url,

            canal_url
        )


        # =================================================
        # CONTEÚDO DA MENSAGEM
        # =================================================

        if mencao:

            content = (
                f"{mencao}\n"
                f"{texto}"
            )

        else:

            content = texto


        # =================================================
        # ENVIAR
        # =================================================

        try:

            await canal_discord.send(

                content=content,

                embed=embed,

                view=view
            )


            print(
                f"📢 Novo vídeo anunciado: "
                f"{titulo}",
                flush=True
            )


        except discord.Forbidden:

            print(
                f"❌ Evelly não possui "
                f"permissão para enviar "
                f"mensagens em "
                f"{guild.name}",
                flush=True
            )


        except discord.HTTPException as erro:

            print(
                f"❌ Discord recusou o anúncio: "
                f"{erro}",
                flush=True
            )


        except Exception as erro:

            print(
                f"❌ Erro enviando anúncio: "
                f"{erro}",
                flush=True
            )


# =========================================================
# SETUP
# =========================================================

async def setup(bot):

    await bot.add_cog(
        YouTube(bot)
    )