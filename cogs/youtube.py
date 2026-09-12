import asyncio
import re
from urllib.parse import urlparse

import aiohttp
import discord

from discord import app_commands
from discord.ext import commands, tasks

from database.database import (
    criar_servidor,
    pegar_servidor,
    adicionar_youtube,
    remover_youtube,
    listar_youtube,
    pegar_todos_youtube,
    atualizar_ultimo_video
)


YOUTUBE_API = "https://www.googleapis.com/youtube/v3"


class YouTube(commands.Cog):

    youtube = app_commands.Group(
        name="youtube",
        description="Sistema de notificações do YouTube."
    )

    def __init__(self, bot):

        self.bot = bot

        self.api_key = bot.youtube_api_key

        self.monitorar.start()

    def cog_unload(self):

        self.monitorar.cancel()

    # =========================================================
    # REQUISIÇÃO À API
    # =========================================================

    async def api_request(self, endpoint, params):

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
                            "❌ Erro na API do YouTube:"
                        )

                        print(texto)

                        return None

                    return await response.json()

        except Exception as erro:

            print(
                f"❌ Erro ao acessar YouTube: {erro}"
            )

            return None

    # =========================================================
    # IDENTIFICAR CANAL
    # =========================================================

    async def obter_canal(self, url):

        url = url.strip()

        # ID direto
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

        # @handle
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

    # =========================================================
    # PEGAR ÚLTIMO VÍDEO
    # =========================================================

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

        itens = dados.get("items", [])

        if not itens:

            return None

        item = itens[0]

        video_id = (
            item
            .get("contentDetails", {})
            .get("videoId")
        )

        return video_id

    # =========================================================
    # /youtube adicionar
    # =========================================================

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

        canal_info = await self.obter_canal(canal)

        if not canal_info:

            await interaction.followup.send(
                "❌ Não consegui encontrar esse canal do YouTube.\n\n"
                "Use um link como:\n"
                "`https://www.youtube.com/@Canal`\n"
                "ou\n"
                "`https://www.youtube.com/channel/UC...`"
            )

            return

        youtube_id = canal_info["id"]

        nome = canal_info["snippet"]["title"]

        uploads_playlist = (
            canal_info
            ["contentDetails"]
            ["relatedPlaylists"]
            ["uploads"]
        )

        ultimo_video = await self.obter_ultimo_video(
            uploads_playlist
        )

        adicionar_youtube(
            guild_id=guild_id,
            youtube_id=youtube_id,
            nome=nome,
            uploads_playlist=uploads_playlist,
            ultimo_video=ultimo_video
        )

        embed = discord.Embed(
            title="✅ Canal adicionado!",
            description=(
                f"A Evelly agora está monitorando "
                f"**{nome}**."
            ),
            color=discord.Color.green()
        )

        embed.add_field(
            name="📺 Canal",
            value=(
                f"https://www.youtube.com/channel/"
                f"{youtube_id}"
            ),
            inline=False
        )

        embed.add_field(
            name="🔔 Próximo vídeo",
            value=(
                "Será anunciado automaticamente "
                "quando um novo vídeo for detectado."
            ),
            inline=False
        )

        await interaction.followup.send(
            embed=embed
        )

    # =========================================================
    # /youtube remover
    # =========================================================

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

    # =========================================================
    # /youtube listar
    # =========================================================

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
                "📺 Nenhum canal do YouTube está sendo monitorado."
            )

            return

        embed = discord.Embed(
            title="📺 Canais monitorados",
            color=discord.Color.red()
        )

        texto = ""

        for youtube_id, nome, ultimo_video, ativo in canais:

            status = "🟢" if ativo else "🔴"

            texto += (
                f"{status} **{nome}**\n"
                f"🆔 `{youtube_id}`\n\n"
            )

        embed.description = texto

        await interaction.response.send_message(
            embed=embed
        )

    # =========================================================
    # /youtube status
    # =========================================================

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

        canal_discord = servidor[1]

        embed = discord.Embed(
            title="🎬 Sistema YouTube",
            color=discord.Color.red()
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

        await interaction.response.send_message(
            embed=embed
        )

    # =========================================================
    # MONITORAMENTO AUTOMÁTICO
    # =========================================================

    @tasks.loop(minutes=2)
    async def monitorar(self):

        await self.bot.wait_until_ready()

        registros = pegar_todos_youtube()

        if not registros:
            return

        print(
            f"📺 Verificando {len(registros)} "
            f"canal(is) do YouTube..."
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

                novo_video = await self.obter_ultimo_video(
                    uploads_playlist
                )

                if not novo_video:
                    continue

                # Primeira execução
                if not ultimo_video:

                    atualizar_ultimo_video(
                        registro_id,
                        novo_video
                    )

                    continue

                # Nada novo
                if novo_video == ultimo_video:

                    continue

                # Novo vídeo encontrado
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

                # Pequena pausa para não sobrecarregar a API
                await asyncio.sleep(1)

            except Exception as erro:

                print(
                    f"❌ Erro monitorando "
                    f"{nome}: {erro}"
                )

    @monitorar.before_loop
    async def antes_monitorar(self):

        await self.bot.wait_until_ready()

    # =========================================================
    # ANÚNCIO
    # =========================================================

    async def anunciar_video(
        self,
        guild_id,
        youtube_id,
        nome,
        video_id
    ):

        guild = self.bot.get_guild(
            guild_id
        )

        if guild is None:
            return

        servidor = pegar_servidor(
            guild_id
        )

        if not servidor:
            return

        canal_id = servidor[1]
        cargo_id = servidor[2]
        mensagem_personalizada = servidor[3]

        if not canal_id:
            print(
                f"⚠️ Servidor {guild_id} "
                f"não possui canal de anúncios."
            )
            return

        canal_discord = guild.get_channel(
            canal_id
        )

        if canal_discord is None:
            return

        video_url = (
            f"https://www.youtube.com/watch?v={video_id}"
        )

        mencao = ""

        if cargo_id:

            cargo = guild.get_role(
                cargo_id
            )

            if cargo:
                mencao = cargo.mention

        if mensagem_personalizada:

            texto = mensagem_personalizada.replace(
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

        else:

            texto = (
                f"🎬 **NOVO VÍDEO!**\n\n"
                f"📺 **{nome}** publicou um novo vídeo!\n"
                f"🔗 {video_url}"
            )

        embed = discord.Embed(
            title="🎬 Novo vídeo no YouTube!",
            description=(
                f"**{nome}** acabou de publicar "
                f"um novo vídeo!"
            ),
            color=discord.Color.red(),
            url=video_url
        )

        embed.set_thumbnail(
            url=(
                f"https://i.ytimg.com/vi/"
                f"{video_id}/hqdefault.jpg"
            )
        )

        embed.add_field(
            name="▶️ Assistir agora",
            value=f"[Clique aqui]({video_url})",
            inline=False
        )

        embed.set_footer(
            text="Evelly • YouTube Notifications"
        )

        try:

            await canal_discord.send(
                content=(
                    f"{mencao}\n"
                    f"{texto}"
                    if mencao
                    else texto
                ),
                embed=embed
            )

            print(
                f"📢 Novo vídeo anunciado: "
                f"{nome}"
            )

        except discord.Forbidden:

            print(
                f"❌ Evelly não possui permissão "
                f"para enviar mensagens em "
                f"{guild.name}"
            )

        except Exception as erro:

            print(
                f"❌ Erro enviando anúncio: {erro}"
            )


async def setup(bot):

    await bot.add_cog(
        YouTube(bot)
    )