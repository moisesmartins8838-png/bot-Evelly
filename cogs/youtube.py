import asyncio
import re
from datetime import datetime, timezone, timedelta

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import View, Button, Select, Modal, TextInput

from database.database import criar_servidor, pegar_servidor
from database.youtube import (
    adicionar_canal,
    remover_canal,
    listar_canais,
    pegar_todos_canais,
    atualizar_ultimo_video,
    atualizar_uploads_playlist,
    salvar_config,
    pegar_config,
    salvar_live,
    live_ja_notificada,
    finalizar_live,
)


YOUTUBE_API = "https://www.googleapis.com/youtube/v3"
INTERVALO_VERIFICACAO = 2


def staff_ok(interaction: discord.Interaction) -> bool:
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        return False
    return (
        interaction.user.guild_permissions.manage_guild
        or interaction.user.guild_permissions.administrator
    )


class YouTubeVideoView(View):
    def __init__(self, video_url: str, channel_url: str):
        super().__init__(timeout=None)
        self.add_item(Button(
            label="Assistir vídeo",
            emoji="▶️",
            style=discord.ButtonStyle.link,
            url=video_url,
        ))
        self.add_item(Button(
            label="Ver canal",
            emoji="📺",
            style=discord.ButtonStyle.link,
            url=channel_url,
        ))


class YouTubeLiveView(View):
    def __init__(self, video_url: str, channel_url: str):
        super().__init__(timeout=None)
        self.add_item(Button(
            label="Assistir LIVE",
            emoji="🔴",
            style=discord.ButtonStyle.link,
            url=video_url,
        ))
        self.add_item(Button(
            label="Ver canal",
            emoji="📺",
            style=discord.ButtonStyle.link,
            url=channel_url,
        ))


class YouTubeChannelModal(Modal, title="Adicionar canal do YouTube"):
    url = TextInput(
        label="URL do canal",
        placeholder="https://www.youtube.com/@Canal",
        required=True,
        max_length=300,
    )

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        info = await self.cog.obter_canal(str(self.url.value))
        if not info:
            await interaction.followup.send(
                "❌ Não encontrei esse canal. Use uma URL `@handle` ou `/channel/UC...`.",
                ephemeral=True,
            )
            return

        channel_id = info["id"]
        name = info["snippet"]["title"]
        uploads = info.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
        latest = await self.cog.obter_ultimo_video(uploads) if uploads else None

        ok = adicionar_canal(
            interaction.guild.id,
            channel_id,
            name,
            uploads,
            latest,
        )
        if not ok:
            await interaction.followup.send(
                "❌ Não consegui salvar o canal no banco.",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            f"✅ **{name}** foi adicionado ao monitoramento.",
            ephemeral=True,
        )


class YouTubePanelView(View):
    def __init__(self, cog):
        super().__init__(timeout=300)
        self.cog = cog

    @discord.ui.button(label="📺 Canais", style=discord.ButtonStyle.primary)
    async def canais(self, interaction: discord.Interaction, button: Button):
        if not staff_ok(interaction):
            await interaction.response.send_message(
                "❌ Você precisa ter **Gerenciar Servidor** para configurar o YouTube.",
                ephemeral=True,
            )
            return

        canais = listar_canais(interaction.guild.id)
        if not canais:
            texto = "Nenhum canal configurado."
        else:
            linhas = []
            for c in canais:
                status = "🟢" if c["ativo"] else "🔴"
                linhas.append(f"{status} **{c['nome']}**\n`{c['youtube_id']}`")
            texto = "\n\n".join(linhas)

        embed = discord.Embed(
            title="📺 Canais monitorados",
            description=texto,
            color=discord.Color.red(),
        )
        view = YouTubeChannelsView(self.cog)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="⚙️ Configuração", style=discord.ButtonStyle.secondary)
    async def configuracao(self, interaction: discord.Interaction, button: Button):
        if not staff_ok(interaction):
            await interaction.response.send_message(
                "❌ Você precisa ter **Gerenciar Servidor**.",
                ephemeral=True,
            )
            return
        await interaction.response.send_modal(YouTubeConfigModal(self.cog))

    @discord.ui.button(label="🧪 Testar", style=discord.ButtonStyle.success)
    async def testar(self, interaction: discord.Interaction, button: Button):
        if not staff_ok(interaction):
            await interaction.response.send_message(
                "❌ Você precisa ter **Gerenciar Servidor**.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            "Escolha o tipo de teste:",
            view=YouTubeTestView(self.cog),
            ephemeral=True,
        )

    @discord.ui.button(label="🔍 Verificar agora", style=discord.ButtonStyle.secondary)
    async def verificar(self, interaction: discord.Interaction, button: Button):
        if not staff_ok(interaction):
            await interaction.response.send_message(
                "❌ Você precisa ter **Gerenciar Servidor**.",
                ephemeral=True,
            )
            return
        await interaction.response.defer(ephemeral=True)
        await self.cog.verificar_todos()
        await interaction.followup.send("✅ Verificação concluída.", ephemeral=True)


class YouTubeChannelsView(View):
    def __init__(self, cog):
        super().__init__(timeout=180)
        self.cog = cog

    @discord.ui.button(label="➕ Adicionar canal", style=discord.ButtonStyle.success)
    async def adicionar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(YouTubeChannelModal(self.cog))

    @discord.ui.button(label="🗑️ Remover canal", style=discord.ButtonStyle.danger)
    async def remover(self, interaction: discord.Interaction, button: Button):
        canais = listar_canais(interaction.guild.id)
        if not canais:
            await interaction.response.send_message("❌ Não há canais.", ephemeral=True)
            return
        await interaction.response.send_message(
            "Envie o ID do canal que deseja remover:",
            ephemeral=True,
        )

        def check(m):
            return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

        try:
            msg = await self.cog.bot.wait_for("message", timeout=30, check=check)
            if remover_canal(interaction.guild.id, msg.content.strip()):
                await interaction.followup.send("✅ Canal removido.", ephemeral=True)
            else:
                await interaction.followup.send("❌ Canal não encontrado.", ephemeral=True)
        except asyncio.TimeoutError:
            await interaction.followup.send("⌛ Tempo esgotado.", ephemeral=True)


class YouTubeTestView(View):
    def __init__(self, cog):
        super().__init__(timeout=60)
        self.cog = cog

    @discord.ui.button(label="🎬 Testar vídeo", style=discord.ButtonStyle.primary)
    async def video(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        await self.cog.enviar_teste(interaction.guild, "video")
        await interaction.followup.send("✅ Teste de vídeo enviado.", ephemeral=True)

    @discord.ui.button(label="🔴 Testar live", style=discord.ButtonStyle.danger)
    async def live(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        await self.cog.enviar_teste(interaction.guild, "live")
        await interaction.followup.send("✅ Teste de live enviado.", ephemeral=True)


class YouTubeConfigModal(Modal, title="Configuração de notificações"):
    canal_video = TextInput(
        label="ID do canal Discord para vídeos",
        placeholder="Deixe vazio para manter atual",
        required=False,
        max_length=30,
    )
    canal_live = TextInput(
        label="ID do canal Discord para lives",
        placeholder="Deixe vazio para manter atual",
        required=False,
        max_length=30,
    )
    cargo_video = TextInput(
        label="ID do cargo para vídeos",
        placeholder="Deixe vazio para manter atual",
        required=False,
        max_length=30,
    )
    cargo_live = TextInput(
        label="ID do cargo para lives",
        placeholder="Deixe vazio para manter atual",
        required=False,
        max_length=30,
    )

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        config = pegar_config(interaction.guild.id) or {}
        dados = {}

        for field, key in [
            (self.canal_video, "video_channel_id"),
            (self.canal_live, "live_channel_id"),
            (self.cargo_video, "video_role_id"),
            (self.cargo_live, "live_role_id"),
        ]:
            value = str(field.value).strip()
            if value:
                try:
                    dados[key] = int(value)
                except ValueError:
                    await interaction.response.send_message(
                        f"❌ `{value}` não é um ID numérico válido.",
                        ephemeral=True,
                    )
                    return

        if not dados:
            await interaction.response.send_message(
                "ℹ️ Nenhuma alteração foi informada.",
                ephemeral=True,
            )
            return

        salvar_config(interaction.guild.id, **dados)
        await interaction.response.send_message(
            "✅ Configuração atualizada.",
            ephemeral=True,
        )


class YouTube(commands.Cog):
    youtube = app_commands.Group(
        name="youtube",
        description="Sistema de vídeos e transmissões do YouTube.",
    )

    def __init__(self, bot):
        self.bot = bot
        self.api_key = bot.youtube_api_key
        self._session = None
        self._quota_bloqueada_ate = None
        self._pending_live = {}
        self._active_live = {}
        self.monitorar.start()
        print("🎬 Sistema YouTube + Streaming iniciado.", flush=True)

    def cog_unload(self):
        self.monitorar.cancel()
        if self._session and not self._session.closed:
            asyncio.create_task(self._session.close())

    async def _fechar_sessao(self):
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None

    def _proximo_reset_quota(self):
        # O reset diário da quota do YouTube ocorre no início do novo dia.
        # Usamos um próximo reset em UTC para não depender do banco de timezones
        # do Windows/Python.
        agora = datetime.now(timezone.utc)
        proximo = (agora + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return proximo

    async def api_request(self, endpoint, params):
        if not self.api_key:
            print("❌ YOUTUBE_API_KEY não configurada.", flush=True)
            return None

        agora = datetime.now(timezone.utc)
        if self._quota_bloqueada_ate and agora < self._quota_bloqueada_ate:
            return None
        if self._quota_bloqueada_ate and agora >= self._quota_bloqueada_ate:
            self._quota_bloqueada_ate = None
            print("🔄 Cota do YouTube liberada após o reset diário.", flush=True)

        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=20)
            self._session = aiohttp.ClientSession(timeout=timeout)

        query = dict(params)
        query["key"] = self.api_key

        try:
            async with self._session.get(f"{YOUTUBE_API}/{endpoint}", params=query) as response:
                data = await response.json(content_type=None)
                if response.status != 200:
                    error = data.get("error", {})
                    errors = error.get("errors", [])
                    reason = errors[0].get("reason") if errors else error.get("status")

                    if response.status == 403 and reason == "quotaExceeded":
                        self._quota_bloqueada_ate = self._proximo_reset_quota()
                        print(
                            "🛑 YouTube API: cota diária esgotada. "
                            f"Monitoramento pausado até {self._quota_bloqueada_ate.isoformat()}.",
                            flush=True,
                        )
                    else:
                        print(
                            f"❌ YouTube API {response.status}: {reason or data}",
                            flush=True,
                        )
                    return None

                return data
        except asyncio.TimeoutError:
            print("⏱️ Timeout na API do YouTube.", flush=True)
        except aiohttp.ClientError as e:
            print(f"❌ Erro HTTP na API do YouTube: {e}", flush=True)
        except Exception as e:
            print(f"❌ Erro na API do YouTube: {e}", flush=True)
        return None

    async def obter_canal(self, url):
        url = url.strip()

        match = re.search(r"(UC[a-zA-Z0-9_-]{20,})", url)
        if match:
            data = await self.api_request(
                "channels",
                {"part": "snippet,contentDetails", "id": match.group(1)},
            )
            return data["items"][0] if data and data.get("items") else None

        match = re.search(r"/@([a-zA-Z0-9._-]+)", url)
        if match:
            data = await self.api_request(
                "channels",
                {"part": "snippet,contentDetails", "forHandle": match.group(1)},
            )
            return data["items"][0] if data and data.get("items") else None

        return None

    async def obter_ultimo_video(self, uploads_playlist):
        if not uploads_playlist:
            return None

        data = await self.api_request(
            "playlistItems",
            {
                "part": "snippet,contentDetails",
                "playlistId": uploads_playlist,
                "maxResults": 1,
            },
        )
        if not data:
            return None

        items = data.get("items", [])
        if not items:
            return None

        return items[0].get("contentDetails", {}).get("videoId")

    async def obter_video(self, video_id):
        data = await self.api_request(
            "videos",
            {
                "part": "snippet,liveStreamingDetails",
                "id": video_id,
            },
        )
        if not data or not data.get("items"):
            return None
        return data["items"][0]

    async def obter_status_video(self, video_id):
        video = await self.obter_video(video_id)
        if not video:
            return None

        snippet = video.get("snippet", {})
        status = snippet.get("liveBroadcastContent", "none")
        detalhes = video.get("liveStreamingDetails", {})

        return {
            "video_id": video_id,
            "status": status,
            "titulo": snippet.get("title", "Live"),
            "descricao": snippet.get("description", ""),
            "thumbnail": (
                snippet.get("thumbnails", {}).get("maxres")
                or snippet.get("thumbnails", {}).get("high")
                or snippet.get("thumbnails", {}).get("default")
                or {}
            ).get("url"),
            "publicado_em": snippet.get("publishedAt"),
            "inicio": detalhes.get("actualStartTime"),
            "fim": detalhes.get("actualEndTime"),
        }

    def canal_url(self, youtube_id):
        return f"https://www.youtube.com/channel/{youtube_id}"

    async def anunciar_video(self, guild_id, youtube_id, nome, video_id):
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return

        config = pegar_config(guild_id) or {}
        channel_id = config.get("video_channel_id") or pegar_servidor(guild_id)[1]
        role_id = config.get("video_role_id") or pegar_servidor(guild_id)[2]

        channel = guild.get_channel(int(channel_id)) if channel_id else None
        if not channel:
            return

        video = await self.obter_video(video_id)
        if not video:
            return

        snippet = video.get("snippet", {})
        title = snippet.get("title", "Novo vídeo")
        desc = snippet.get("description", "").strip()
        thumb = (snippet.get("thumbnails", {}).get("maxres")
                 or snippet.get("thumbnails", {}).get("high")
                 or snippet.get("thumbnails", {}).get("default")
                 or {}).get("url")

        url = f"https://www.youtube.com/watch?v={video_id}"
        embed = discord.Embed(
            title=f"🎬 {title}",
            description=f"📺 **{nome}**\n\n{desc[:500] or 'Um novo vídeo foi publicado.'}",
            color=discord.Color.red(),
            url=url,
        )
        embed.set_author(name=f"🔴 {nome}", url=self.canal_url(youtube_id))
        if thumb:
            embed.set_image(url=thumb)
        embed.add_field(name="▶️ Vídeo", value=f"[Assistir no YouTube]({url})", inline=True)
        embed.set_footer(text="Evelly LN • YouTube")

        content = ""
        if role_id:
            role = guild.get_role(int(role_id))
            if role:
                content = role.mention

        await channel.send(
            content=content or None,
            embed=embed,
            view=YouTubeVideoView(url, self.canal_url(youtube_id)),
        )

    async def anunciar_live(self, guild_id, youtube_id, nome, live):
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return

        config = pegar_config(guild_id) or {}
        channel_id = config.get("live_channel_id") or config.get("video_channel_id")
        role_id = config.get("live_role_id") or config.get("video_role_id")

        if not channel_id:
            servidor = pegar_servidor(guild_id)
            channel_id = servidor[1] if servidor else None
            role_id = servidor[2] if servidor else None

        channel = guild.get_channel(int(channel_id)) if channel_id else None
        if not channel:
            return

        url = f"https://www.youtube.com/watch?v={live['video_id']}"
        embed = discord.Embed(
            title="🔴 ESTÁ AO VIVO AGORA!",
            description=(
                f"📺 **{nome}**\n\n"
                f"🎥 **{live['titulo']}**\n\n"
                f"{live['descricao'][:500] or 'Uma nova transmissão ao vivo começou.'}"
            ),
            color=discord.Color.dark_red(),
            url=url,
        )
        embed.set_author(name=f"🔴 {nome}", url=self.canal_url(youtube_id))
        if live.get("thumbnail"):
            embed.set_image(url=live["thumbnail"])
        embed.add_field(name="🔴 Status", value="**AO VIVO**", inline=True)
        embed.add_field(name="▶️ Transmissão", value=f"[Assistir LIVE]({url})", inline=True)
        embed.set_footer(text="Evelly LN • Live Notifications")

        content = ""
        if role_id:
            role = guild.get_role(int(role_id))
            if role:
                content = role.mention

        await channel.send(
            content=content or None,
            embed=embed,
            view=YouTubeLiveView(url, self.canal_url(youtube_id)),
        )

    async def processar_canal(self, registro):
        record_id = registro["id"]
        guild_id = registro["guild_id"]
        youtube_id = registro["youtube_id"]
        name = registro["nome"]
        uploads = registro.get("uploads_playlist")
        last_video = registro.get("ultimo_video")
        state_key = (guild_id, youtube_id)

        if self._quota_bloqueada_ate and datetime.now(timezone.utc) < self._quota_bloqueada_ate:
            print(
                f"[YT] ⏸️ Quota bloqueada — ignorando {name}.",
                flush=True,
            )
            return

        print(f"[YT] 🔎 Verificando: {name} ({youtube_id})", flush=True)

        novo_video = await self.obter_ultimo_video(uploads)

        # Se a playlist estiver inválida/desatualizada, recupera automaticamente.
        if not novo_video:
            print(f"[YT] ⚠️ Não encontrei vídeo pela playlist de {name}. Tentando recuperar...", flush=True)
            canal = await self.obter_canal(youtube_id)
            if canal:
                new_uploads = (
                    canal.get("contentDetails", {})
                    .get("relatedPlaylists", {})
                    .get("uploads")
                )
                if new_uploads and new_uploads != uploads:
                    atualizar_uploads_playlist(record_id, new_uploads)
                    uploads = new_uploads
                    print(f"[YT] ♻️ Playlist de uploads atualizada para {name}.", flush=True)
                    novo_video = await self.obter_ultimo_video(new_uploads)

        if not novo_video:
            print(f"[YT] ❌ Nenhum vídeo encontrado para {name}.", flush=True)
            return

        mudou_video = novo_video != last_video
        print(
            f"[YT] 📹 Último vídeo: {novo_video} | "
            f"{'NOVO' if mudou_video else 'mesmo vídeo'}",
            flush=True,
        )

        # IMPORTANTE:
        # Mesmo que o ID do vídeo não tenha mudado, ele pode ter acabado de
        # entrar em LIVE. Por isso consultamos videos.list em todos os ciclos.
        info = await self.obter_status_video(novo_video)
        if not info:
            print(f"[YT] ❌ Não consegui consultar o status de {novo_video}.", flush=True)
            return

        status = info["status"]
        print(f"[YT] 📡 Status de {novo_video}: {status}", flush=True)

        if status == "upcoming":
            self._pending_live[state_key] = novo_video
            self._active_live.pop(state_key, None)

            if mudou_video:
                atualizar_ultimo_video(record_id, novo_video)

            print(f"[YT] 🟡 Live agendada detectada: {name}", flush=True)
            return

        if status == "live":
            self._pending_live.pop(state_key, None)

            # Detecta a transição para LIVE mesmo quando o ID do vídeo não mudou.
            era_ativa = state_key in self._active_live
            self._active_live[state_key] = novo_video

            if not era_ativa:
                print(f"[YT] 🔴 LIVE DETECTADA: {name} — {info['titulo']}", flush=True)

            if not live_ja_notificada(guild_id, youtube_id, novo_video):
                print(f"[YT] 📢 Enviando notificação de LIVE para {name}...", flush=True)

                try:
                    await self.anunciar_live(guild_id, youtube_id, name, info)

                    salvar_live(
                        guild_id,
                        youtube_id,
                        novo_video,
                        info["titulo"],
                        info.get("inicio") or info.get("publicado_em"),
                        True,
                    )

                    print(f"[YT] ✅ Notificação de LIVE enviada: {name}", flush=True)
                except Exception as e:
                    print(
                        f"[YT] ❌ Erro enviando notificação de LIVE para {name}: {e}",
                        flush=True,
                    )
                    raise
            else:
                print(f"[YT] ℹ️ LIVE já notificada anteriormente: {name}", flush=True)

            if mudou_video:
                atualizar_ultimo_video(record_id, novo_video)

            return

        # Status normal/encerrado.
        if state_key in self._active_live:
            print(f"[YT] ⏹️ LIVE encerrada: {name}", flush=True)
            finalizar_live(guild_id, youtube_id)
            self._active_live.pop(state_key, None)

        self._pending_live.pop(state_key, None)

        if mudou_video:
            atualizar_ultimo_video(record_id, novo_video)

            # O vídeo só é anunciado como vídeo normal se não estiver/estava em live.
            print(f"[YT] 🎬 Novo vídeo normal detectado: {name}", flush=True)
            try:
                await self.anunciar_video(guild_id, youtube_id, name, novo_video)
                print(f"[YT] ✅ Notificação de vídeo enviada: {name}", flush=True)
            except Exception as e:
                print(
                    f"[YT] ❌ Erro enviando notificação de vídeo para {name}: {e}",
                    flush=True,
                )
                raise

    async def verificar_todos(self):
        registros = pegar_todos_canais()
        if not registros:
            print("[YT] ℹ️ Nenhum canal configurado para monitorar.", flush=True)
            return

        print(f"[YT] 📺 {len(registros)} canal(is) no monitoramento.", flush=True)

        for registro in registros:
            try:
                await self.processar_canal(registro)
            except Exception as e:
                print(f"❌ Erro monitorando {registro.get('nome')}: {e}", flush=True)
            await asyncio.sleep(1)

    @tasks.loop(minutes=INTERVALO_VERIFICACAO)
    async def monitorar(self):
        print(
            f"[YT] 🔄 Iniciando ciclo de monitoramento ({INTERVALO_VERIFICACAO} min)...",
            flush=True,
        )
        await self.verificar_todos()
        print("[YT] ✅ Ciclo de monitoramento concluído.", flush=True)

    @monitorar.before_loop
    async def before_monitorar(self):
        await self.bot.wait_until_ready()

    async def enviar_teste(self, guild, tipo):
        config = pegar_config(guild.id) or {}
        channel_id = (
            config.get("live_channel_id") if tipo == "live"
            else config.get("video_channel_id")
        )
        if not channel_id:
            servidor = pegar_servidor(guild.id)
            channel_id = servidor[1] if servidor else None

        channel = guild.get_channel(int(channel_id)) if channel_id else None
        if not channel:
            return

        if tipo == "live":
            embed = discord.Embed(
                title="🔴 ESTÁ AO VIVO AGORA!",
                description="📺 **Canal de teste**\n\n🎥 **Live de teste da Evelly**",
                color=discord.Color.dark_red(),
            )
            embed.add_field(name="🔴 Status", value="**AO VIVO**")
            await channel.send(embed=embed)
        else:
            embed = discord.Embed(
                title="🎬 Novo vídeo — TESTE",
                description="📺 **Canal de teste**\n\nEsta é uma notificação de vídeo de teste.",
                color=discord.Color.red(),
            )
            await channel.send(embed=embed)

    @youtube.command(name="painel", description="Abre o painel de configuração do YouTube.")
    async def painel(self, interaction: discord.Interaction):
        if not staff_ok(interaction):
            await interaction.response.send_message(
                "❌ Você precisa ter **Gerenciar Servidor**.",
                ephemeral=True,
            )
            return

        criar_servidor(interaction.guild.id)
        config = pegar_config(interaction.guild.id) or {}
        canais = listar_canais(interaction.guild.id)

        embed = discord.Embed(
            title="🎬 EVELLY • YOUTUBE",
            description="Configure vídeos, transmissões ao vivo e canais monitorados.",
            color=discord.Color.red(),
        )
        embed.add_field(name="📺 Canais monitorados", value=str(len(canais)), inline=True)
        embed.add_field(
            name="🔴 Lives",
            value="Sistema ativo",
            inline=True,
        )
        embed.add_field(
            name="⏱️ Verificação",
            value=f"A cada {INTERVALO_VERIFICACAO} minutos",
            inline=True,
        )
        embed.add_field(
            name="🎬 Canal de vídeos",
            value=f"<#{config['video_channel_id']}>" if config.get("video_channel_id") else "Usando canal geral",
            inline=False,
        )
        embed.add_field(
            name="🔴 Canal de lives",
            value=f"<#{config['live_channel_id']}>" if config.get("live_channel_id") else "Mesmo canal de vídeos",
            inline=False,
        )
        embed.set_footer(text="Evelly LN • YouTube & Streaming")

        await interaction.response.send_message(
            embed=embed,
            view=YouTubePanelView(self),
            ephemeral=True,
        )

    @youtube.command(name="status", description="Mostra o status do sistema YouTube.")
    async def status(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("❌ Use em um servidor.", ephemeral=True)
            return
        canais = listar_canais(interaction.guild.id)
        config = pegar_config(interaction.guild.id) or {}
        embed = discord.Embed(
            title="🎬 YouTube & Streaming",
            color=discord.Color.green(),
        )
        embed.add_field(name="📺 Canais", value=str(len(canais)), inline=True)
        embed.add_field(name="🔴 Lives", value="🟢 Monitoradas", inline=True)
        embed.add_field(
            name="⏱️ Intervalo",
            value=f"{INTERVALO_VERIFICACAO} minutos",
            inline=True,
        )
        embed.add_field(
            name="📢 Vídeos",
            value=f"<#{config['video_channel_id']}>" if config.get("video_channel_id") else "Canal geral",
            inline=True,
        )
        embed.add_field(
            name="🔴 Lives",
            value=f"<#{config['live_channel_id']}>" if config.get("live_channel_id") else "Canal de vídeos",
            inline=True,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @youtube.command(name="verificar", description="Força uma verificação imediata.")
    async def verificar(self, interaction: discord.Interaction):
        if not staff_ok(interaction):
            await interaction.response.send_message(
                "❌ Você precisa ter **Gerenciar Servidor**.",
                ephemeral=True,
            )
            return
        await interaction.response.defer(ephemeral=True)
        await self.verificar_todos()
        await interaction.followup.send("✅ Verificação realizada.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(YouTube(bot))
