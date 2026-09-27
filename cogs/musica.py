import asyncio
import os
import random
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
import wavelink

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


# Lavalink/Wavelink resolve o áudio no servidor.
# Não precisamos mais de cookies do YouTube nem de FFmpeg local.



@dataclass
class Song:
    title: str
    webpage_url: str
    stream_url: str = ""
    duration: Optional[int] = None
    thumbnail: Optional[str] = None
    requester_id: Optional[int] = None
    requester_name: str = ""
    track: Optional[wavelink.Playable] = None


@dataclass
class GuildMusic:
    queue: list[Song] = field(default_factory=list)
    current: Optional[Song] = None
    voice: Optional[wavelink.Player] = None
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
            await interaction.response.send_message("❌ A Evelly não está em uma call.", ephemeral=True)
            return
        if state.voice.playing:
            await state.voice.pause(True)
            await interaction.response.send_message("⏸️ Música pausada.", ephemeral=True)
        elif state.voice.paused:
            await interaction.response.send_message("ℹ️ A música já está pausada.", ephemeral=True)
        else:
            await interaction.response.send_message("ℹ️ Não existe música tocando.", ephemeral=True)

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
            await interaction.response.send_message("❌ A Evelly não está em uma call.", ephemeral=True)
            return
        if state.voice.paused:
            await state.voice.pause(False)
            await interaction.response.send_message("▶️ Música retomada.", ephemeral=True)
        else:
            await interaction.response.send_message("ℹ️ A música não está pausada.", ephemeral=True)

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
        if not state or not state.voice or not state.playing:
            await interaction.response.send_message("❌ Não existe música tocando.", ephemeral=True)
            return
        state.loop = "off" if state.loop == "song" else state.loop
        await state.voice.stop()
        await interaction.response.send_message("⏭️ Música pulada.", ephemeral=True)

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
            await interaction.response.send_message("❌ Nenhuma sessão de música ativa.", ephemeral=True)
            return
        state.queue.clear()
        state.loop = "off"
        if state.voice:
            try:
                await state.voice.stop()
            except Exception:
                pass
        state.current = None
        state.playing = False
        await interaction.response.send_message("⏹️ Reprodução parada e fila limpa.", ephemeral=True)

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
            await interaction.response.send_message("❌ A Evelly não está em uma call.", ephemeral=True)
            return
        await state.voice.disconnect(force=True)
        state.voice = None
        state.queue.clear()
        state.current = None
        state.playing = False
        await interaction.response.send_message("👋 Saí da call e limpei a fila.", ephemeral=True)



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
        print("🎵 Motor: Wavelink + Lavalink", flush=True)

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
                if state.voice and state.voice.connected:
                    if state.voice.channel != member.voice.channel:
                        await state.voice.move_to(member.voice.channel)
                    await interaction.followup.send(
                        f"🔊 Estou na call {member.voice.channel.mention}.",
                        ephemeral=True,
                    )
                    return

                state.voice = await member.voice.channel.connect(cls=wavelink.Player)
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
                if state.voice is None or not state.voice.connected:
                    state.voice = await member.voice.channel.connect(cls=wavelink.Player)
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

            if state.voice.playing:
                await state.voice.pause(True)
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
            if state and state.voice and state.voice.paused:
                await state.voice.pause(False)
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
            if not state or not state.voice or not state.voice.playing:
                await interaction.response.send_message(
                    "❌ Não há música tocando.",
                    ephemeral=True,
                )
                return

            await state.voice.stop()
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

            if state.voice and (state.voice.playing or state.voice.paused):
                await state.voice.stop()

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

            if state.voice:
                await state.voice.set_volume(int(state.volume * 100))

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
        """Pesquisa/resolva a faixa usando o plugin do YouTube no Lavalink."""
        try:
            target = query.strip()
            if not target.startswith(("http://", "https://")):
                target = f"ytsearch:{target}"

            result = await wavelink.Playable.search(target)
            if not result:
                return None

            track = result.tracks[0] if isinstance(result, wavelink.Playlist) else result[0]
            duration_ms = getattr(track, "length", 0) or 0
            thumbnail = getattr(track, "artwork", None)
            webpage_url = getattr(track, "uri", None) or query

            return Song(
                title=getattr(track, "title", "Sem título"),
                webpage_url=webpage_url,
                duration=int(duration_ms / 1000) if duration_ms else None,
                thumbnail=thumbnail,
                requester_id=requester.id,
                requester_name=requester.display_name,
                track=track,
            )
        except Exception as error:
            print(f"[MUSICA] Erro pesquisando no Lavalink: {error}", flush=True)
            return None

    async def refresh_stream_url(self, song: Song) -> Song:
        """Compatibilidade estrutural: o Lavalink gerencia o stream automaticamente."""
        return song

    async def play_next(self, guild_id: int):
        state = self.states.get(guild_id)

        if not state or not state.voice or not state.voice.connected:
            return

        if state.starting:
            return

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
                        await channel.send("📭 A fila terminou.")
                    except Exception:
                        pass
                return

            song = state.queue.pop(0)
            state.current = song

        if not song.track:
            state.current = None
            state.playing = False
            await self.play_next(guild_id)
            return

        state.starting = True

        try:
            await state.voice.play(song.track)
            await state.voice.set_volume(int(state.volume * 100))
            state.playing = True

            channel = self.bot.get_channel(state.text_channel_id or 0)
            if channel:
                try:
                    embed = self.song_embed(song, title="▶️ Tocando agora")
                    await channel.send(embed=embed)
                except Exception as error:
                    print(f"[MUSICA] Erro enviando agora: {error}", flush=True)

        except Exception as error:
            print(f"[MUSICA] Falha ao iniciar {song.title}: {error}", flush=True)
            state.current = None
            state.playing = False
            channel = self.bot.get_channel(state.text_channel_id or 0)
            if channel:
                try:
                    await channel.send(f"⚠️ Não consegui reproduzir **{song.title}**. Pulando para a próxima.")
                except Exception:
                    pass
            await self.play_next(guild_id)
        finally:
            state.starting = False

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload):
        player = payload.player
        if not player or not player.guild:
            return
        state = self.states.get(player.guild.id)
        if not state:
            return
        state.playing = False
        await asyncio.sleep(0.25)
        if state.voice and state.voice.connected:
            await self.play_next(player.guild.id)

    @commands.Cog.listener()
    async def on_wavelink_track_exception(self, payload):
        player = payload.player
        if not player or not player.guild:
            return
        state = self.states.get(player.guild.id)
        if not state:
            return
        print(f"[MUSICA] Erro Lavalink na guild {player.guild.id}: {payload.exception}", flush=True)
        state.playing = False
        channel = self.bot.get_channel(state.text_channel_id or 0)
        if channel:
            try:
                await channel.send("⚠️ O Lavalink encontrou um erro nessa música. Tentando a próxima.")
            except Exception:
                pass
        await asyncio.sleep(0.25)
        await self.play_next(player.guild.id)

    @commands.Cog.listener()
    async def on_wavelink_track_stuck(self, payload):
        player = payload.player
        if not player or not player.guild:
            return
        state = self.states.get(player.guild.id)
        if not state:
            return
        state.playing = False
        try:
            await player.stop()
        except Exception:
            pass
        await asyncio.sleep(0.25)
        await self.play_next(player.guild.id)

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload):
        print(f"🎵 Lavalink pronto: {payload.node.identifier}", flush=True)

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
            if state.voice and state.voice.connected:
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
