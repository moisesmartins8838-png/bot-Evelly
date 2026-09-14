import asyncio
import re
import traceback
from collections import deque
from dataclasses import dataclass
from typing import Optional

import discord
import yt_dlp
from discord import app_commands
from discord.ext import commands


# ============================================================
# CONFIGURAÇÕES
# ============================================================

DEFAULT_VOLUME = 0.70

# Opções usadas pelo yt-dlp.
YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
}

# Opções do FFmpeg.
FFMPEG_OPTIONS = {
    "before_options": (
        "-reconnect 1 "
        "-reconnect_streamed 1 "
        "-reconnect_delay_max 5"
    ),
    "options": "-vn",
}


# ============================================================
# MODELO DE MÚSICA
# ============================================================

@dataclass
class Musica:
    titulo: str
    url: str
    webpage_url: str
    duracao: Optional[int]
    solicitante: str


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def formatar_duracao(segundos: Optional[int]) -> str:
    if not segundos:
        return "Desconhecida"

    minutos, segundos_restantes = divmod(int(segundos), 60)
    horas, minutos = divmod(minutos, 60)

    if horas:
        return f"{horas}:{minutos:02d}:{segundos_restantes:02d}"

    return f"{minutos}:{segundos_restantes:02d}"


def parece_link(texto: str) -> bool:
    return bool(
        re.match(
            r"^https?://",
            texto.strip(),
            re.IGNORECASE
        )
    )


def obter_info_youtube(consulta: str) -> dict:
    """
    Pesquisa no YouTube ou abre diretamente um link.
    Essa função é síncrona, então será executada em thread
    para não travar o bot.
    """

    with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:

        if parece_link(consulta):
            alvo = consulta
        else:
            alvo = f"ytsearch1:{consulta}"

        info = ydl.extract_info(
            alvo,
            download=False
        )

        if not info:
            raise RuntimeError(
                "Não foi possível encontrar a música."
            )

        # Pesquisa do YouTube retorna uma playlist de resultados.
        if "entries" in info:
            entradas = [
                entrada
                for entrada in info["entries"]
                if entrada
            ]

            if not entradas:
                raise RuntimeError(
                    "Nenhum resultado encontrado no YouTube."
                )

            info = entradas[0]

        url_audio = info.get("url")

        if not url_audio:
            raise RuntimeError(
                "Não foi possível obter o áudio dessa música."
            )

        return {
            "titulo": info.get("title", "Música desconhecida"),
            "url": url_audio,
            "webpage_url": info.get(
                "webpage_url",
                consulta
            ),
            "duracao": info.get("duration"),
        }


# ============================================================
# VIEW DOS BOTÕES
# ============================================================

class ControlesMusica(discord.ui.View):

    def __init__(self, cog: "MusicaCog"):
        super().__init__(timeout=300)
        self.cog = cog

    @discord.ui.button(
        label="⏸️ Pausar",
        style=discord.ButtonStyle.secondary
    )
    async def pausar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if not self.cog.pode_controlar(interaction):
            await interaction.response.send_message(
                "❌ Você precisa estar na mesma call que a Evelly.",
                ephemeral=True
            )
            return

        voice = interaction.guild.voice_client

        if not voice or not voice.is_connected():
            await interaction.response.send_message(
                "❌ A Evelly não está em uma call.",
                ephemeral=True
            )
            return

        if voice.is_playing():
            voice.pause()

            await interaction.response.send_message(
                "⏸️ Música pausada.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "⚠️ Não existe uma música tocando agora.",
            ephemeral=True
        )

    @discord.ui.button(
        label="▶️ Continuar",
        style=discord.ButtonStyle.success
    )
    async def continuar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if not self.cog.pode_controlar(interaction):
            await interaction.response.send_message(
                "❌ Você precisa estar na mesma call que a Evelly.",
                ephemeral=True
            )
            return

        voice = interaction.guild.voice_client

        if not voice or not voice.is_connected():
            await interaction.response.send_message(
                "❌ A Evelly não está em uma call.",
                ephemeral=True
            )
            return

        if voice.is_paused():
            voice.resume()

            await interaction.response.send_message(
                "▶️ Música retomada.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "⚠️ A música não está pausada.",
            ephemeral=True
        )

    @discord.ui.button(
        label="⏭️ Pular",
        style=discord.ButtonStyle.primary
    )
    async def pular(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if not self.cog.pode_controlar(interaction):
            await interaction.response.send_message(
                "❌ Você precisa estar na mesma call que a Evelly.",
                ephemeral=True
            )
            return

        voice = interaction.guild.voice_client

        if not voice or not voice.is_connected():
            await interaction.response.send_message(
                "❌ A Evelly não está em uma call.",
                ephemeral=True
            )
            return

        if not voice.is_playing() and not voice.is_paused():
            await interaction.response.send_message(
                "⚠️ Não existe uma música tocando.",
                ephemeral=True
            )
            return

        voice.stop()

        await interaction.response.send_message(
            "⏭️ Pulando música...",
            ephemeral=True
        )

    @discord.ui.button(
        label="⏹️ Parar",
        style=discord.ButtonStyle.danger
    )
    async def parar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if not self.cog.pode_controlar(interaction):
            await interaction.response.send_message(
                "❌ Você precisa estar na mesma call que a Evelly.",
                ephemeral=True
            )
            return

        voice = interaction.guild.voice_client

        if not voice or not voice.is_connected():
            await interaction.response.send_message(
                "❌ A Evelly não está em uma call.",
                ephemeral=True
            )
            return

        self.cog.limpar_fila(interaction.guild.id)

        voice.stop()

        await interaction.response.send_message(
            "⏹️ Reprodução parada e fila limpa.",
            ephemeral=True
        )

    @discord.ui.button(
        label="🔊 Volume",
        style=discord.ButtonStyle.secondary
    )
    async def volume(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if not self.cog.pode_controlar(interaction):
            await interaction.response.send_message(
                "❌ Você precisa estar na mesma call que a Evelly.",
                ephemeral=True
            )
            return

        volume = self.cog.volumes.get(
            interaction.guild.id,
            DEFAULT_VOLUME
        )

        await interaction.response.send_message(
            f"🔊 Volume atual: **{int(volume * 100)}%**\n"
            f"Use `/volume 10-100` para alterar.",
            ephemeral=True
        )


# ============================================================
# COG
# ============================================================

class MusicaCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # guild_id -> fila
        self.filas: dict[int, deque[Musica]] = {}

        # guild_id -> música atual
        self.atual: dict[int, Optional[Musica]] = {}

        # guild_id -> volume
        self.volumes: dict[int, float] = {}

        # guild_id -> canal de texto onde a música foi solicitada
        self.canais_texto: dict[int, int] = {}

        # guild_id -> trava de reprodução
        self.travas: dict[int, asyncio.Lock] = {}

    # ========================================================
    # FILAS
    # ========================================================

    def obter_fila(self, guild_id: int) -> deque:
        if guild_id not in self.filas:
            self.filas[guild_id] = deque()

        return self.filas[guild_id]

    def obter_trava(self, guild_id: int) -> asyncio.Lock:
        if guild_id not in self.travas:
            self.travas[guild_id] = asyncio.Lock()

        return self.travas[guild_id]

    def limpar_fila(self, guild_id: int):
        self.obter_fila(guild_id).clear()
        self.atual[guild_id] = None

    # ========================================================
    # PERMISSÕES
    # ========================================================

    def pode_controlar(
        self,
        interaction: discord.Interaction
    ) -> bool:

        if not interaction.guild:
            return False

        voice_client = interaction.guild.voice_client

        if not voice_client:
            return False

        usuario = interaction.user

        if not isinstance(usuario, discord.Member):
            return False

        if not usuario.voice:
            return False

        return (
            usuario.voice.channel.id
            == voice_client.channel.id
        )

    # ========================================================
    # ENTRAR NA CALL
    # ========================================================

    async def conectar_na_call(
        self,
        interaction: discord.Interaction
    ) -> discord.VoiceClient:

        if not interaction.guild:
            raise RuntimeError(
                "Esse comando precisa ser usado em um servidor."
            )

        usuario = interaction.user

        if not isinstance(usuario, discord.Member):
            raise RuntimeError(
                "Não consegui identificar seu usuário."
            )

        if not usuario.voice or not usuario.voice.channel:
            raise RuntimeError(
                "Você precisa estar em um canal de voz."
            )

        canal = usuario.voice.channel
        voice = interaction.guild.voice_client

        if voice:

            if voice.channel.id != canal.id:
                await voice.move_to(canal)

            return voice

        voice = await canal.connect()

        return voice

    # ========================================================
    # EXTRAIR MÚSICA
    # ========================================================

    async def pesquisar_musica(
        self,
        consulta: str,
        solicitante: str
    ) -> Musica:

        loop = asyncio.get_running_loop()

        info = await loop.run_in_executor(
            None,
            obter_info_youtube,
            consulta
        )

        return Musica(
            titulo=info["titulo"],
            url=info["url"],
            webpage_url=info["webpage_url"],
            duracao=info["duracao"],
            solicitante=solicitante
        )

    # ========================================================
    # REPRODUÇÃO
    # ========================================================

    async def iniciar_proxima(
        self,
        guild_id: int
    ):

        guild = self.bot.get_guild(guild_id)

        if not guild:
            return

        voice = guild.voice_client

        if not voice or not voice.is_connected():
            return

        if voice.is_playing() or voice.is_paused():
            return

        fila = self.obter_fila(guild_id)

        if not fila:
            self.atual[guild_id] = None
            return

        musica = fila.popleft()

        self.atual[guild_id] = musica

        try:
            source = discord.FFmpegPCMAudio(
                musica.url,
                **FFMPEG_OPTIONS
            )

            volume = self.volumes.get(
                guild_id,
                DEFAULT_VOLUME
            )

            source = discord.PCMVolumeTransformer(
                source,
                volume=volume
            )

            def terminou(error):
                if error:
                    print(
                        f"[MÚSICA] Erro na reprodução: {error}"
                    )

                asyncio.run_coroutine_threadsafe(
                    self.reproducao_terminou(guild_id),
                    self.bot.loop
                )

            voice.play(
                source,
                after=terminou
            )

            canal_id = self.canais_texto.get(guild_id)

            if canal_id:
                canal = guild.get_channel(canal_id)

                if canal:
                    embed = discord.Embed(
                        title="🎵 Tocando agora",
                        description=(
                            f"**[{musica.titulo}]"
                            f"({musica.webpage_url})**"
                        ),
                        color=discord.Color.blurple()
                    )

                    embed.add_field(
                        name="⏱️ Duração",
                        value=formatar_duracao(
                            musica.duracao
                        ),
                        inline=True
                    )

                    embed.add_field(
                        name="👤 Pedido por",
                        value=musica.solicitante,
                        inline=True
                    )

                    await canal.send(
                        embed=embed,
                        view=ControlesMusica(self)
                    )

        except Exception as erro:
            print(
                f"[MÚSICA] Erro ao iniciar reprodução: {erro}"
            )

            traceback.print_exc()

            self.atual[guild_id] = None

            await self.iniciar_proxima(guild_id)

    async def reproducao_terminou(
        self,
        guild_id: int
    ):

        self.atual[guild_id] = None

        await asyncio.sleep(1)

        guild = self.bot.get_guild(guild_id)

        if not guild:
            return

        voice = guild.voice_client

        if not voice or not voice.is_connected():
            return

        await self.iniciar_proxima(guild_id)

    # ========================================================
    # /MUSICA
    # ========================================================

    @app_commands.command(
        name="musica",
        description="Toca uma música do YouTube na sua call."
    )
    @app_commands.describe(
        consulta="Nome da música ou link do YouTube"
    )
    async def musica(
        self,
        interaction: discord.Interaction,
        consulta: str
    ):
        """
        Comando principal de música.

        IMPORTANTE:
        O defer() acontece imediatamente para evitar que a interação
        do Discord expire enquanto o bot valida a call ou pesquisa
        a música no YouTube.
        """

        # Confirma a interação imediatamente.
        #
        # Em condições normais, is_done() deve ser False aqui.
        # Se alguma outra rotina/instância já tiver confirmado esta
        # interação, não tentamos confirmar novamente: seguimos usando
        # followup, que é a forma correta de responder após uma interação
        # já reconhecida.
        interacao_ja_confirmada = interaction.response.is_done()

        if interacao_ja_confirmada:
            print(
                f"[MÚSICA] Interação {interaction.id} já estava confirmada "
                "antes do /musica."
            )
        else:
            try:
                await interaction.response.defer()
            except discord.NotFound:
                print(
                    "[MÚSICA] A interação do /musica expirou antes do defer()."
                )
                return
            except discord.HTTPException as erro:
                # 40060 significa que a interação foi confirmada por outra
                # rotina/instância entre o is_done() e o defer().
                if getattr(erro, "code", None) == 40060:
                    print(
                        f"[MÚSICA] Interação {interaction.id} já foi "
                        "confirmada externamente (40060). Continuando "
                        "com followup."
                    )
                    interacao_ja_confirmada = True
                else:
                    print(
                        f"[MÚSICA] Não foi possível confirmar a interação: "
                        f"{erro}"
                    )
                    return

        try:
            # Depois do defer(), TODAS as respostas devem usar followup.
            if not interaction.guild:
                await interaction.followup.send(
                    "❌ Esse comando só pode ser usado em um servidor.",
                    ephemeral=True
                )
                return

            usuario = interaction.user

            if not isinstance(usuario, discord.Member):
                await interaction.followup.send(
                    "❌ Não consegui identificar você.",
                    ephemeral=True
                )
                return

            if not usuario.voice or not usuario.voice.channel:
                await interaction.followup.send(
                    "❌ Você precisa estar em uma call primeiro.",
                    ephemeral=True
                )
                return

            guild_id = interaction.guild.id

            # Pesquisa primeiro. O yt-dlp roda em outra thread,
            # então não bloqueia o loop principal do Discord.
            musica = await self.pesquisar_musica(
                consulta,
                usuario.display_name
            )

            # Entra/move a Evelly para a call.
            voice = await self.conectar_na_call(interaction)

            fila = self.obter_fila(guild_id)
            fila.append(musica)

            if interaction.channel:
                self.canais_texto[guild_id] = interaction.channel.id

            esta_tocando = (
                voice.is_playing()
                or voice.is_paused()
            )

            if esta_tocando:
                posicao = len(fila)

                embed = discord.Embed(
                    title="🎵 Música adicionada à fila",
                    description=(
                        f"**[{musica.titulo}]"
                        f"({musica.webpage_url})**"
                    ),
                    color=discord.Color.blurple()
                )

                embed.add_field(
                    name="📍 Posição",
                    value=f"#{posicao}",
                    inline=True
                )

                embed.add_field(
                    name="⏱️ Duração",
                    value=formatar_duracao(musica.duracao),
                    inline=True
                )

                await interaction.followup.send(embed=embed)

            else:
                await self.iniciar_proxima(guild_id)

                embed = discord.Embed(
                    title="🎵 Preparando música",
                    description=(
                        f"**[{musica.titulo}]"
                        f"({musica.webpage_url})**"
                    ),
                    color=discord.Color.green()
                )

                await interaction.followup.send(embed=embed)

        except Exception as erro:
            print(f"[MÚSICA] Erro no /musica: {erro}")
            traceback.print_exc()

            # Como o defer() já foi feito, nunca usamos
            # interaction.response.send_message() aqui.
            try:
                await interaction.followup.send(
                    "❌ **Não consegui tocar essa música.**\n\n"
                    f"Detalhes: `{erro}`",
                    ephemeral=True
                )
            except discord.NotFound:
                print("[MÚSICA] A interação expirou antes do envio do erro.")
            except discord.HTTPException as followup_erro:
                print(
                    f"[MÚSICA] Não foi possível enviar a mensagem de erro: "
                    f"{followup_erro}"
                )


    # ========================================================
    # /PAUSAR
    # ========================================================

    @app_commands.command(
        name="pausar",
        description="Pausa a música atual."
    )
    async def pausar(
        self,
        interaction: discord.Interaction
    ):

        if not self.pode_controlar(interaction):
            await interaction.response.send_message(
                "❌ Você precisa estar na mesma call que a Evelly.",
                ephemeral=True
            )
            return

        voice = interaction.guild.voice_client

        if voice.is_playing():
            voice.pause()

            await interaction.response.send_message(
                "⏸️ Música pausada."
            )
            return

        await interaction.response.send_message(
            "⚠️ Nenhuma música está tocando.",
            ephemeral=True
        )

    # ========================================================
    # /CONTINUAR
    # ========================================================

    @app_commands.command(
        name="continuar",
        description="Continua a música pausada."
    )
    async def continuar(
        self,
        interaction: discord.Interaction
    ):

        if not self.pode_controlar(interaction):
            await interaction.response.send_message(
                "❌ Você precisa estar na mesma call que a Evelly.",
                ephemeral=True
            )
            return

        voice = interaction.guild.voice_client

        if voice.is_paused():
            voice.resume()

            await interaction.response.send_message(
                "▶️ Música retomada."
            )
            return

        await interaction.response.send_message(
            "⚠️ A música não está pausada.",
            ephemeral=True
        )

    # ========================================================
    # /PULAR
    # ========================================================

    @app_commands.command(
        name="pular",
        description="Pula a música atual."
    )
    async def pular(
        self,
        interaction: discord.Interaction
    ):

        if not self.pode_controlar(interaction):
            await interaction.response.send_message(
                "❌ Você precisa estar na mesma call que a Evelly.",
                ephemeral=True
            )
            return

        voice = interaction.guild.voice_client

        if not voice.is_playing() and not voice.is_paused():
            await interaction.response.send_message(
                "⚠️ Nenhuma música está tocando.",
                ephemeral=True
            )
            return

        voice.stop()

        await interaction.response.send_message(
            "⏭️ Música pulada."
        )

    # ========================================================
    # /PARAR
    # ========================================================

    @app_commands.command(
        name="parar",
        description="Para a música e limpa a fila."
    )
    async def parar(
        self,
        interaction: discord.Interaction
    ):

        if not self.pode_controlar(interaction):
            await interaction.response.send_message(
                "❌ Você precisa estar na mesma call que a Evelly.",
                ephemeral=True
            )
            return

        voice = interaction.guild.voice_client

        self.limpar_fila(
            interaction.guild.id
        )

        if voice:
            voice.stop()

        await interaction.response.send_message(
            "⏹️ Reprodução parada e fila limpa."
        )

    # ========================================================
    # /FILA
    # ========================================================

    @app_commands.command(
        name="fila",
        description="Mostra as músicas da fila."
    )
    async def fila(
        self,
        interaction: discord.Interaction
    ):

        if not interaction.guild:
            return

        fila = self.obter_fila(
            interaction.guild.id
        )

        atual = self.atual.get(
            interaction.guild.id
        )

        if not atual and not fila:
            await interaction.response.send_message(
                "📭 A fila está vazia.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🎵 Fila da Evelly",
            color=discord.Color.blurple()
        )

        if atual:
            embed.add_field(
                name="▶️ Tocando agora",
                value=(
                    f"**[{atual.titulo}]"
                    f"({atual.webpage_url})**"
                ),
                inline=False
            )

        if fila:

            lista = []

            for i, musica in enumerate(
                list(fila)[:10],
                start=1
            ):
                lista.append(
                    f"`{i}.` [{musica.titulo}]"
                    f"({musica.webpage_url})"
                )

            embed.add_field(
                name=f"📋 Próximas ({len(fila)})",
                value="\n".join(lista),
                inline=False
            )

            if len(fila) > 10:
                embed.set_footer(
                    text=(
                        f"+ {len(fila) - 10} músicas "
                        "não exibidas."
                    )
                )

        await interaction.response.send_message(
            embed=embed
        )

    # ========================================================
    # /VOLUME
    # ========================================================

    @app_commands.command(
        name="volume",
        description="Altera o volume da Evelly."
    )
    @app_commands.describe(
        porcentagem="Volume de 1 a 100"
    )
    async def volume(
        self,
        interaction: discord.Interaction,
        porcentagem: app_commands.Range[int, 1, 100]
    ):

        if not self.pode_controlar(interaction):
            await interaction.response.send_message(
                "❌ Você precisa estar na mesma call que a Evelly.",
                ephemeral=True
            )
            return

        volume = porcentagem / 100

        self.volumes[
            interaction.guild.id
        ] = volume

        voice = interaction.guild.voice_client

        if voice and voice.source:
            source = voice.source

            if isinstance(
                source,
                discord.PCMVolumeTransformer
            ):
                source.volume = volume

        await interaction.response.send_message(
            f"🔊 Volume alterado para **{porcentagem}%**."
        )

    # ========================================================
    # /SAIR
    # ========================================================

    @app_commands.command(
        name="sair",
        description="Faz a Evelly sair da call."
    )
    async def sair(
        self,
        interaction: discord.Interaction
    ):

        if not interaction.guild:
            return

        voice = interaction.guild.voice_client

        if not voice:
            await interaction.response.send_message(
                "❌ A Evelly não está em uma call.",
                ephemeral=True
            )
            return

        if not self.pode_controlar(interaction):
            await interaction.response.send_message(
                "❌ Você precisa estar na mesma call que a Evelly.",
                ephemeral=True
            )
            return

        self.limpar_fila(
            interaction.guild.id
        )

        await voice.disconnect()

        await interaction.response.send_message(
            "👋 Saí da call!"
        )


# ============================================================
# SETUP
# ============================================================

async def setup(bot: commands.Bot):
    await bot.add_cog(MusicaCog(bot))
