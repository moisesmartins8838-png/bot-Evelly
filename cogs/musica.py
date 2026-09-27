import asyncio
import os
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp

try:
    import imageio_ffmpeg
except ImportError:
    imageio_ffmpeg = None

from cogs.permissoes import pode_controlar_evelly


# ============================================================
# EVELLY MUSIC SYSTEM
# ============================================================
# Comandos:
# /musica entrar
# /musica play
# /musica pause
# /musica continuar
# /musica skip
# /musica parar
# /musica sair
# /musica fila
# /musica agora
# /musica volume
# /musica loop
# /musica shuffle
# /musica remover
# /musica painel
#
# O sistema trabalha por servidor (guild).
# A fila é mantida em memória. O bot pode continuar tocando
# após erros de uma faixa, mas uma reinicialização limpa a fila.
# ============================================================


PURPLE = 0x8E44AD
MUSIC_PREFIX = "evelly_music_"

BASE_DIR = Path(__file__).resolve().parent.parent
COOKIES_FILE = BASE_DIR / "cookies.txt"


def ffmpeg_executable() -> str:
    """Retorna um FFmpeg disponível no ambiente."""
    custom = os.getenv("FFMPEG_PATH")
    if custom and Path(custom).exists():
        return custom

    if imageio_ffmpeg is not None:
        try:
            path = imageio_ffmpeg.get_ffmpeg_exe()
            if path:
                return path
        except Exception:
            pass

    return "ffmpeg"


YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
    "extract_flat": False,
    "skip_download": True,
}

if COOKIES_FILE.exists():
    YTDL_OPTIONS["cookiefile"] = str(COOKIES_FILE)


@dataclass
class Song:
    title: str
    webpage_url: str
    stream_url: str = ""
    duration: Optional[int] = None
    thumbnail: Optional[str] = None
    requester_id: Optional[int] = None
    requester_name: str = ""


@dataclass
class GuildMusic:
    queue: list[Song] = field(default_factory=list)
    current: Optional[Song] = None
    voice: Optional[discord.VoiceClient] = None
    volume: float = 0.60
    loop: str = "off"  # off / song / queue
    text_channel_id: Optional[int] = None
    playing: bool = False
    starting: bool = False


class MusicControlView(discord.ui.View):
    """Painel persistente de controles da música."""

    def __init__(self, cog: "Musica"):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="Pausar",
        emoji="⏸️",
        style=discord.ButtonStyle.secondary,
        custom_id=f"{MUSIC_PREFIX}pause",
    )
    async def pause(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        state = self.cog.states.get(interaction.guild_id)
        if not state or not state.voice:
            await interaction.response.send_message(
                "❌ A Evelly não está em uma call.",
                ephemeral=True,
            )
            return

        if state.voice.is_playing():
            state.voice.pause()
            await interaction.response.send_message(
                "⏸️ Música pausada.",
                ephemeral=True,
            )
        elif state.voice.is_paused():
            await interaction.response.send_message(
                "ℹ️ A música já está pausada.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "ℹ️ Não existe música tocando.",
                ephemeral=True,
            )

    @discord.ui.button(
        label="Continuar",
        emoji="▶️",
        style=discord.ButtonStyle.success,
        custom_id=f"{MUSIC_PREFIX}resume",
    )
    async def resume(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        state = self.cog.states.get(interaction.guild_id)
        if not state or not state.voice:
            await interaction.response.send_message(
                "❌ A Evelly não está em uma call.",
                ephemeral=True,
            )
            return

        if state.voice.is_paused():
            state.voice.resume()
            await interaction.response.send_message(
                "▶️ Música retomada.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "ℹ️ A música não está pausada.",
                ephemeral=True,
            )

    @discord.ui.button(
        label="Pular",
        emoji="⏭️",
        style=discord.ButtonStyle.primary,
        custom_id=f"{MUSIC_PREFIX}skip",
    )
    async def skip(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        state = self.cog.states.get(interaction.guild_id)
        if not state or not state.voice or not state.voice.is_playing():
            await interaction.response.send_message(
                "❌ Não existe música tocando.",
                ephemeral=True,
            )
            return

        state.loop = "off" if state.loop == "song" else state.loop
        state.voice.stop()

        await interaction.response.send_message(
            "⏭️ Música pulada.",
            ephemeral=True,
        )

    @discord.ui.button(
        label="Parar",
        emoji="⏹️",
        style=discord.ButtonStyle.danger,
        custom_id=f"{MUSIC_PREFIX}stop",
    )
    async def stop(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        state = self.cog.states.get(interaction.guild_id)
        if not state:
            await interaction.response.send_message(
                "❌ Nenhuma sessão de música ativa.",
                ephemeral=True,
            )
            return

        state.queue.clear()
        state.loop = "off"

        if state.voice and state.voice.is_playing():
            state.voice.stop()

        state.current = None
        state.playing = False

        await interaction.response.send_message(
            "⏹️ Reprodução parada e fila limpa.",
            ephemeral=True,
        )

    @discord.ui.button(
        label="Sair",
        emoji="👋",
        style=discord.ButtonStyle.secondary,
        custom_id=f"{MUSIC_PREFIX}leave",
    )
    async def leave(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        state = self.cog.states.get(interaction.guild_id)
        if not state or not state.voice:
            await interaction.response.send_message(
                "❌ A Evelly não está em uma call.",
                ephemeral=True,
            )
            return

        await state.voice.disconnect(force=True)
        state.voice = None
        state.queue.clear()
        state.current = None
        state.playing = False

        await interaction.response.send_message(
            "👋 Saí da call e limpei a fila.",
            ephemeral=True,
        )


class Musica(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.states: dict[int, GuildMusic] = {}
        self.music_group = app_commands.Group(
            name="musica",
            description="Sistema de música da Evelly.",
        )

        self._register_commands()

        print("🎵 Sistema de música da Evelly carregado.", flush=True)
        print(f"🎵 FFmpeg: {ffmpeg_executable()}", flush=True)

    def _register_commands(self):
        # ----------------------------------------------------
        # ENTRAR
        # ----------------------------------------------------
        @self.music_group.command(
            name="entrar",
            description="Faz a Evelly entrar na sua call.",
        )
        async def entrar(interaction: discord.Interaction):
            if not interaction.guild:
                await interaction.response.send_message(
                    "❌ Esse comando só pode ser usado em servidor.",
                    ephemeral=True,
                )
                return

            member = interaction.user
            if not isinstance(member, discord.Member) or not member.voice:
                await interaction.response.send_message(
                    "❌ Entre em uma call primeiro.",
                    ephemeral=True,
                )
                return

            await interaction.response.defer(ephemeral=True)

            state = self.get_state(interaction.guild.id)

            try:
                if state.voice and state.voice.is_connected():
                    if state.voice.channel != member.voice.channel:
                        await state.voice.move_to(member.voice.channel)
                    await interaction.followup.send(
                        f"🔊 Estou na call {member.voice.channel.mention}.",
                        ephemeral=True,
                    )
                    return

                state.voice = await member.voice.channel.connect()
                state.text_channel_id = interaction.channel_id

                await interaction.followup.send(
                    f"🎵 Entrei em {member.voice.channel.mention}.",
                    ephemeral=True,
                )

            except Exception as error:
                print(f"[MUSICA] Erro entrando na call: {error}", flush=True)
                await interaction.followup.send(
                    f"❌ Não consegui entrar na call.\n`{error}`",
                    ephemeral=True,
                )

        # ----------------------------------------------------
        # PLAY
        # ----------------------------------------------------
        @self.music_group.command(
            name="play",
            description="Pesquisa ou toca uma música.",
        )
        @app_commands.describe(
            busca="Nome da música ou URL do YouTube.",
        )
        async def play(
            interaction: discord.Interaction,
            busca: str,
        ):
            if not interaction.guild:
                await interaction.response.send_message(
                    "❌ Use este comando em um servidor.",
                    ephemeral=True,
                )
                return

            member = interaction.user
            if not isinstance(member, discord.Member) or not member.voice:
                await interaction.response.send_message(
                    "❌ Entre em uma call primeiro.",
                    ephemeral=True,
                )
                return

            await interaction.response.defer()

            state = self.get_state(interaction.guild.id)
            state.text_channel_id = interaction.channel_id

            try:
                if state.voice is None or not state.voice.is_connected():
                    state.voice = await member.voice.channel.connect()
                elif state.voice.channel != member.voice.channel:
                    await state.voice.move_to(member.voice.channel)

                song = await self.resolve_song(
                    busca,
                    interaction.user,
                )

                if not song:
                    await interaction.followup.send(
                        "❌ Não encontrei essa música."
                    )
                    return

                state.queue.append(song)

                embed = self.song_embed(
                    song,
                    title="🎵 Adicionada à fila",
                )
                embed.set_footer(
                    text=f"Solicitada por {interaction.user.display_name}"
                )

                await interaction.followup.send(embed=embed)

                if not state.playing and not state.starting:
                    await self.play_next(interaction.guild.id)

            except Exception as error:
                print(
                    f"[MUSICA] Erro no /musica play: {error}",
                    flush=True,
                )
                await interaction.followup.send(
                    f"❌ Não consegui tocar essa música.\n`{error}`"
                )

        # ----------------------------------------------------
        # PAUSE
        # ----------------------------------------------------
        @self.music_group.command(
            name="pause",
            description="Pausa a música atual.",
        )
        async def pause(interaction: discord.Interaction):
            state = self.states.get(interaction.guild_id)
            if not state or not state.voice:
                await interaction.response.send_message(
                    "❌ Não estou tocando música.",
                    ephemeral=True,
                )
                return

            if state.voice.is_playing():
                state.voice.pause()
                await interaction.response.send_message("⏸️ Música pausada.")
            else:
                await interaction.response.send_message(
                    "ℹ️ Não há música tocando.",
                    ephemeral=True,
                )

        # ----------------------------------------------------
        # CONTINUAR
        # ----------------------------------------------------
        @self.music_group.command(
            name="continuar",
            description="Continua a música pausada.",
        )
        async def continuar(interaction: discord.Interaction):
            state = self.states.get(interaction.guild_id)
            if state and state.voice and state.voice.is_paused():
                state.voice.resume()
                await interaction.response.send_message("▶️ Música retomada.")
            else:
                await interaction.response.send_message(
                    "ℹ️ Não há música pausada.",
                    ephemeral=True,
                )

        # ----------------------------------------------------
        # SKIP
        # ----------------------------------------------------
        @self.music_group.command(
            name="skip",
            description="Pula a música atual.",
        )
        async def skip(interaction: discord.Interaction):
            state = self.states.get(interaction.guild_id)
            if not state or not state.voice or not state.voice.is_playing():
                await interaction.response.send_message(
                    "❌ Não há música tocando.",
                    ephemeral=True,
                )
                return

            state.voice.stop()
            await interaction.response.send_message("⏭️ Música pulada.")

        # ----------------------------------------------------
        # PARAR
        # ----------------------------------------------------
        @self.music_group.command(
            name="parar",
            description="Para a música e limpa a fila.",
        )
        async def parar(interaction: discord.Interaction):
            state = self.states.get(interaction.guild_id)
            if not state:
                await interaction.response.send_message(
                    "❌ Nenhuma sessão de música ativa.",
                    ephemeral=True,
                )
                return

            state.queue.clear()
            state.loop = "off"

            if state.voice and (state.voice.is_playing() or state.voice.is_paused()):
                state.voice.stop()

            state.current = None
            state.playing = False

            await interaction.response.send_message(
                "⏹️ Reprodução parada e fila limpa."
            )

        # ----------------------------------------------------
        # SAIR
        # ----------------------------------------------------
        @self.music_group.command(
            name="sair",
            description="Faz a Evelly sair da call.",
        )
        async def sair(interaction: discord.Interaction):
            state = self.states.get(interaction.guild_id)

            if not state or not state.voice:
                await interaction.response.send_message(
                    "❌ Não estou em uma call.",
                    ephemeral=True,
                )
                return

            await state.voice.disconnect(force=True)
            state.voice = None
            state.queue.clear()
            state.current = None
            state.playing = False
            state.loop = "off"

            await interaction.response.send_message(
                "👋 Saí da call e limpei a fila."
            )

        # ----------------------------------------------------
        # FILA
        # ----------------------------------------------------
        @self.music_group.command(
            name="fila",
            description="Mostra a fila de músicas.",
        )
        async def fila(interaction: discord.Interaction):
            state = self.states.get(interaction.guild_id)

            if not state or (not state.current and not state.queue):
                await interaction.response.send_message(
                    "📭 A fila está vazia.",
                    ephemeral=True,
                )
                return

            embed = discord.Embed(
                title="🎵 Fila da Evelly",
                color=PURPLE,
            )

            if state.current:
                embed.add_field(
                    name="▶️ Tocando agora",
                    value=f"**{state.current.title}**",
                    inline=False,
                )

            if state.queue:
                linhas = []
                for index, song in enumerate(state.queue[:20], start=1):
                    linhas.append(
                        f"`{index:02}` • **{song.title[:80]}**"
                    )

                if len(state.queue) > 20:
                    linhas.append(
                        f"\n... e mais {len(state.queue) - 20} música(s)."
                    )

                embed.add_field(
                    name="📜 Próximas",
                    value="\n".join(linhas),
                    inline=False,
                )

            embed.set_footer(
                text=f"Loop: {state.loop} • Volume: {int(state.volume * 100)}%"
            )

            await interaction.response.send_message(embed=embed)

        # ----------------------------------------------------
        # AGORA
        # ----------------------------------------------------
        @self.music_group.command(
            name="agora",
            description="Mostra a música atual.",
        )
        async def agora(interaction: discord.Interaction):
            state = self.states.get(interaction.guild_id)

            if not state or not state.current:
                await interaction.response.send_message(
                    "❌ Nada está tocando.",
                    ephemeral=True,
                )
                return

            embed = self.song_embed(
                state.current,
                title="🎶 Tocando agora",
            )
            embed.add_field(
                name="🔊 Volume",
                value=f"{int(state.volume * 100)}%",
            )
            embed.add_field(
                name="🔁 Loop",
                value=state.loop,
            )

            await interaction.response.send_message(embed=embed)

        # ----------------------------------------------------
        # VOLUME
        # ----------------------------------------------------
        @self.music_group.command(
            name="volume",
            description="Altera o volume da música.",
        )
        @app_commands.describe(
            valor="Volume de 0 a 100.",
        )
        async def volume(
            interaction: discord.Interaction,
            valor: app_commands.Range[int, 0, 100],
        ):
            state = self.get_state(interaction.guild_id)
            state.volume = valor / 100

            if state.voice and state.voice.source:
                source = state.voice.source
                if isinstance(source, discord.PCMVolumeTransformer):
                    source.volume = state.volume

            await interaction.response.send_message(
                f"🔊 Volume definido para **{valor}%**."
            )

        # ----------------------------------------------------
        # LOOP
        # ----------------------------------------------------
        @self.music_group.command(
            name="loop",
            description="Alterna o modo de repetição.",
        )
        @app_commands.describe(
            modo="off = desligado, song = música, queue = fila.",
        )
        @app_commands.choices(
            modo=[
                app_commands.Choice(name="Desligado", value="off"),
                app_commands.Choice(name="Música atual", value="song"),
                app_commands.Choice(name="Fila inteira", value="queue"),
            ]
        )
        async def loop(
            interaction: discord.Interaction,
            modo: app_commands.Choice[str],
        ):
            state = self.get_state(interaction.guild_id)
            state.loop = modo.value

            nomes = {
                "off": "desligado",
                "song": "música atual",
                "queue": "fila inteira",
            }

            await interaction.response.send_message(
                f"🔁 Loop **{nomes[modo.value]}**."
            )

        # ----------------------------------------------------
        # SHUFFLE
        # ----------------------------------------------------
        @self.music_group.command(
            name="shuffle",
            description="Embaralha a fila.",
        )
        async def shuffle(interaction: discord.Interaction):
            state = self.states.get(interaction.guild_id)

            if not state or len(state.queue) < 2:
                await interaction.response.send_message(
                    "ℹ️ É preciso ter pelo menos 2 músicas na fila.",
                    ephemeral=True,
                )
                return

            random.shuffle(state.queue)

            await interaction.response.send_message(
                "🔀 Fila embaralhada."
            )

        # ----------------------------------------------------
        # REMOVER
        # ----------------------------------------------------
        @self.music_group.command(
            name="remover",
            description="Remove uma posição da fila.",
        )
        @app_commands.describe(
            posicao="Número da música na fila.",
        )
        async def remover(
            interaction: discord.Interaction,
            posicao: app_commands.Range[int, 1, 100],
        ):
            state = self.states.get(interaction.guild_id)

            if not state or posicao > len(state.queue):
                await interaction.response.send_message(
                    "❌ Essa posição não existe na fila.",
                    ephemeral=True,
                )
                return

            song = state.queue.pop(posicao - 1)

            await interaction.response.send_message(
                f"🗑️ Removida: **{song.title}**"
            )

        # ----------------------------------------------------
        # PAINEL
        # ----------------------------------------------------
        @self.music_group.command(
            name="painel",
            description="Publica o painel de controles da música.",
        )
        async def painel(interaction: discord.Interaction):
            if not pode_controlar_evelly(interaction.user):
                await interaction.response.send_message(
                    "❌ Você não possui permissão para publicar o painel.",
                    ephemeral=True,
                )
                return

            embed = discord.Embed(
                title="🎵 Evelly Music",
                description=(
                    "Controle a reprodução da música usando os botões abaixo.\n\n"
                    "🎶 Use `/musica play` para adicionar músicas.\n"
                    "📜 Use `/musica fila` para visualizar a fila.\n"
                    "🔊 Use `/musica volume` para alterar o volume.\n"
                    "🔁 Use `/musica loop` para configurar repetição."
                ),
                color=PURPLE,
            )
            embed.set_footer(
                text="Evelly • Sistema de Música"
            )

            await interaction.channel.send(
                embed=embed,
                view=MusicControlView(self),
            )

            await interaction.response.send_message(
                "✅ Painel de música publicado.",
                ephemeral=True,
            )

    def get_state(self, guild_id: int) -> GuildMusic:
        state = self.states.get(guild_id)
        if state is None:
            state = GuildMusic()
            self.states[guild_id] = state
        return state

    async def resolve_song(
        self,
        query: str,
        requester: discord.abc.User,
    ) -> Optional[Song]:
        """Resolve URL ou pesquisa do YouTube fora do event loop."""
        def extract():
            target = query.strip()

            if not target.startswith(("http://", "https://")):
                target = f"ytsearch1:{target}"

            options = dict(YTDL_OPTIONS)

            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(
                    target,
                    download=False,
                )

                if not info:
                    return None

                if "entries" in info:
                    entries = [
                        item for item in info.get("entries", [])
                        if item
                    ]
                    if not entries:
                        return None
                    info = entries[0]

                return {
                    "title": info.get("title") or "Sem título",
                    "webpage_url": (
                        info.get("webpage_url")
                        or info.get("original_url")
                        or query
                    ),
                    "stream_url": info.get("url") or "",
                    "duration": info.get("duration"),
                    "thumbnail": info.get("thumbnail"),
                }

        data = await asyncio.to_thread(extract)

        if not data:
            return None

        return Song(
            title=data["title"],
            webpage_url=data["webpage_url"],
            stream_url=data["stream_url"],
            duration=data["duration"],
            thumbnail=data["thumbnail"],
            requester_id=requester.id,
            requester_name=requester.display_name,
        )

    async def refresh_stream_url(self, song: Song) -> Song:
        """Obtém uma URL de áudio fresca para evitar expiração."""
        def extract():
            options = dict(YTDL_OPTIONS)
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(
                    song.webpage_url,
                    download=False,
                )

                if "entries" in info:
                    entries = [
                        item for item in info.get("entries", [])
                        if item
                    ]
                    if not entries:
                        raise RuntimeError("Música não encontrada.")
                    info = entries[0]

                return info.get("url")

        url = await asyncio.to_thread(extract)

        if not url:
            raise RuntimeError("Não foi possível obter o áudio.")

        song.stream_url = url
        return song

    async def play_next(self, guild_id: int):
        state = self.states.get(guild_id)

        if not state or not state.voice or not state.voice.is_connected():
            return

        if state.starting:
            return

        # Loop da música atual.
        if state.current and state.loop == "song":
            song = state.current
        else:
            if state.current and state.loop == "queue":
                state.queue.append(state.current)

            if not state.queue:
                state.current = None
                state.playing = False

                channel = self.bot.get_channel(state.text_channel_id or 0)
                if channel:
                    try:
                        await channel.send(
                            "📭 A fila terminou."
                        )
                    except Exception:
                        pass
                return

            song = state.queue.pop(0)
            state.current = song

        state.starting = True

        try:
            song = await self.refresh_stream_url(song)

            ffmpeg = ffmpeg_executable()

            before_options = (
                "-reconnect 1 "
                "-reconnect_streamed 1 "
                "-reconnect_delay_max 5"
            )

            options = (
                "-vn "
                "-loglevel warning "
                "-ac 2 "
                "-ar 48000"
            )

            source = discord.FFmpegPCMAudio(
                song.stream_url,
                executable=ffmpeg,
                before_options=before_options,
                options=options,
            )

            source = discord.PCMVolumeTransformer(
                source,
                volume=state.volume,
            )

            def after_play(error):
                if error:
                    print(
                        f"[MUSICA] Erro de reprodução em "
                        f"{guild_id}: {error}",
                        flush=True,
                    )

                future = asyncio.run_coroutine_threadsafe(
                    self.handle_after(guild_id),
                    self.bot.loop,
                )

                try:
                    future.result(timeout=1)
                except Exception:
                    pass

            state.voice.play(
                source,
                after=after_play,
            )

            state.playing = True

            channel = self.bot.get_channel(
                state.text_channel_id or 0
            )

            if channel:
                try:
                    embed = self.song_embed(
                        song,
                        title="▶️ Tocando agora",
                    )
                    await channel.send(embed=embed)
                except Exception as error:
                    print(
                        f"[MUSICA] Erro enviando agora: {error}",
                        flush=True,
                    )

        except Exception as error:
            print(
                f"[MUSICA] Falha ao iniciar {song.title}: {error}",
                flush=True,
            )

            channel = self.bot.get_channel(
                state.text_channel_id or 0
            )

            if channel:
                try:
                    await channel.send(
                        f"⚠️ Não consegui reproduzir "
                        f"**{song.title}**. Pulando para a próxima."
                    )
                except Exception:
                    pass

            state.current = None
            state.playing = False

            await self.play_next(guild_id)

        finally:
            state.starting = False

    async def handle_after(self, guild_id: int):
        state = self.states.get(guild_id)

        if not state:
            return

        state.playing = False

        # Se a sessão ainda existe, continua automaticamente.
        await asyncio.sleep(0.5)

        if state.voice and state.voice.is_connected():
            await self.play_next(guild_id)

    def song_embed(
        self,
        song: Song,
        title: str,
    ) -> discord.Embed:
        embed = discord.Embed(
            title=title,
            description=f"**{song.title}**",
            color=PURPLE,
            url=song.webpage_url,
        )

        if song.thumbnail:
            embed.set_thumbnail(url=song.thumbnail)

        if song.duration:
            minutes, seconds = divmod(int(song.duration), 60)
            hours, minutes = divmod(minutes, 60)

            if hours:
                duration = f"{hours}:{minutes:02}:{seconds:02}"
            else:
                duration = f"{minutes}:{seconds:02}"

            embed.add_field(
                name="⏱️ Duração",
                value=duration,
            )

        if song.requester_name:
            embed.add_field(
                name="👤 Solicitada por",
                value=song.requester_name,
            )

        return embed

    async def cog_load(self):
        # Registra o grupo /musica na árvore de comandos.
        self.bot.tree.add_command(self.music_group)

        # View persistente para painéis já publicados antes de restart.
        self.bot.add_view(MusicControlView(self))

    def cog_unload(self):
        for state in self.states.values():
            if state.voice and state.voice.is_connected():
                asyncio.create_task(
                    state.voice.disconnect(force=True)
                )

    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        """Sai da call quando a Evelly fica sozinha."""
        if member.id != self.bot.user.id:
            return

        state = self.states.get(member.guild.id)
        if not state or not state.voice:
            return

        # O próprio bot mudou de canal; não fazemos nada aqui.
        return


async def setup(bot: commands.Bot):
    await bot.add_cog(Musica(bot))
    print("🎵 cogs.musica carregado com sucesso.", flush=True)
