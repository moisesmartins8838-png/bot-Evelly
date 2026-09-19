import re
from pathlib import Path
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

from database.database import (
    criar_auto_message,
    pegar_auto_messages_pendentes,
    pegar_auto_message,
    atualizar_auto_message,
    excluir_auto_message,
    registrar_auto_message_log,
)

from cogs.permissoes import pode_controlar_evelly


DEFAULT_COLOR = 0x8E44AD
PROCESS_INTERVAL_SECONDS = 60

BASE_DIR = Path(__file__).resolve().parent.parent
BANNER_PATH = BASE_DIR / "resource" / "ln_store_banner.png"

INVITE_REGEX = re.compile(
    r"(?:https?://)?(?:www\.)?(?:discord\.gg/|discord\.com/invite/)([A-Za-z0-9-]+)",
    re.IGNORECASE,
)


def now_utc():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.isoformat()


def parse_dt(value):
    if not value:
        return None

    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    try:
        return datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        )
    except Exception:
        return None


def encontrar_convite(texto):
    if not texto:
        return None

    match = INVITE_REGEX.search(str(texto))

    if not match:
        return None

    return f"https://discord.gg/{match.group(1)}"


class AutoMensagem(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.processar_automsg.start()

        print(
            "📨 cogs.automsg carregado com sucesso",
            flush=True,
        )

    def cog_unload(self):
        self.processar_automsg.cancel()

    # =========================================================
    # ÍCONE DO SERVIDOR DO CONVITE
    # =========================================================

    async def obter_icone_servidor(self, convite_url):
        try:
            convite = await self.bot.fetch_invite(
                convite_url,
                with_counts=False,
            )

            servidor = convite.guild

            if not servidor:
                return None

            icone = getattr(
                servidor,
                "icon",
                None,
            )

            if icone:
                return icone.url

        except Exception as erro:
            print(
                f"[AUTOMSG] Não foi possível obter o ícone "
                f"do convite {convite_url}: {erro}",
                flush=True,
            )

        return None

    # =========================================================
    # EMBED PREMIUM
    # =========================================================

    async def montar_embed(self, item):
        mensagem = str(
            item.get("content") or ""
        ).strip()

        embed = discord.Embed(
            title="📢  AVISO AUTOMÁTICO",
            description=(
                f"💜 **{mensagem[:4096]}**"
                if mensagem
                else "💜 **Aviso da comunidade**"
            ),
            color=DEFAULT_COLOR,
        )

        # Banner da Evelly no topo.
        if BANNER_PATH.exists():
            embed.set_image(
                url="attachment://ln_store_banner.png"
            )

        # Detecta convite na própria mensagem.
        convite_url = encontrar_convite(
            mensagem
        )

        if convite_url:

            icone_url = await self.obter_icone_servidor(
                convite_url
            )

            # Somente o ícone do servidor.
            if icone_url:
                embed.set_thumbnail(
                    url=icone_url
                )

            # Área final do card.
            embed.add_field(
                name="",
                value="━━━━━━━━━━━━━━━━━━━━",
                inline=False,
            )

            embed.add_field(
                name="🌐  Comunidade",
                value=(
                    f"🔗 [**ENTRAR NA COMUNIDADE →**]"
                    f"({convite_url})"
                ),
                inline=False,
            )

        embed.set_footer(
            text="Evelly • LN Premium • Aviso automático"
        )

        return embed

    # =========================================================
    # ENVIAR
    # =========================================================

    async def enviar_automacao(self, guild, item):
        channel_id = item.get("channel_id")

        if not channel_id:
            return None, False, "Canal não configurado."

        channel = guild.get_channel(
            int(channel_id)
        )

        if channel is None:
            try:
                channel = await self.bot.fetch_channel(
                    int(channel_id)
                )
            except Exception as erro:
                return None, False, (
                    f"Não consegui acessar o canal: {erro}"
                )

        embed = await self.montar_embed(
            item
        )

        arquivo = None

        if BANNER_PATH.exists():
            arquivo = discord.File(
                BANNER_PATH,
                filename="ln_store_banner.png",
            )

        try:

            kwargs = {
                "embed": embed,
            }

            if arquivo:
                kwargs["file"] = arquivo

            mensagem = await channel.send(
                **kwargs
            )

            return mensagem, True, "Mensagem enviada."

        except Exception as erro:
            return None, False, str(erro)

    # =========================================================
    # /AUTOMSG
    # =========================================================

    @app_commands.command(
        name="automsg",
        description="Cria uma mensagem automática em embed premium.",
    )
    @app_commands.describe(
        canal="Canal onde a mensagem será enviada.",
        mensagem="Mensagem que aparecerá no embed.",
        tempo="Intervalo entre os envios, em dias.",
    )
    async def automsg(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel,
        mensagem: str,
        tempo: app_commands.Range[int, 1, 365],
    ):

        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Este comando só pode ser usado em um servidor.",
                ephemeral=True,
            )
            return

        if not pode_controlar_evelly(
            interaction.user
        ):
            await interaction.response.send_message(
                "❌ Você não possui permissão para usar a AutoMensagem.",
                ephemeral=True,
            )
            return

        mensagem = mensagem.strip()

        if not mensagem:
            await interaction.response.send_message(
                "❌ A mensagem não pode estar vazia.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(
            ephemeral=True
        )

        agora = now_utc()
        intervalo = int(tempo)

        try:

            auto_id = criar_auto_message(
                guild_id=interaction.guild.id,
                channel_id=canal.id,
                title="📢 Aviso automático",
                description="",
                content=mensagem,
                color=DEFAULT_COLOR,
                interval_days=intervalo,
                mode="history",
                message_id=None,
                next_send_at=iso(agora),
                created_by=interaction.user.id,
            )

            if isinstance(auto_id, dict):
                auto_id = auto_id.get("id")

            if not auto_id:
                await interaction.followup.send(
                    "❌ Não consegui salvar a AutoMensagem no Supabase.",
                    ephemeral=True,
                )
                return

            auto_id = int(auto_id)

            item = {
                "id": auto_id,
                "guild_id": interaction.guild.id,
                "channel_id": canal.id,
                "title": "📢 Aviso automático",
                "description": "",
                "content": mensagem,
                "color": DEFAULT_COLOR,
                "interval_days": intervalo,
                "mode": "history",
                "enabled": True,
                "message_id": None,
                "last_sent_at": None,
                "next_send_at": iso(agora),
            }

            msg, ok, detalhes = (
                await self.enviar_automacao(
                    interaction.guild,
                    item,
                )
            )

            if not ok:

                atualizar_auto_message(
                    auto_id,
                    next_send_at=iso(
                        agora + timedelta(minutes=5)
                    ),
                )

                registrar_auto_message_log(
                    auto_id,
                    interaction.guild.id,
                    canal.id,
                    "create_error",
                    None,
                    detalhes,
                )

                await interaction.followup.send(
                    "⚠️ A automação foi criada, "
                    "mas o primeiro envio falhou.\n\n"
                    f"{detalhes}",
                    ephemeral=True,
                )
                return

            proximo = (
                agora
                + timedelta(days=intervalo)
            )

            atualizar_auto_message(
                auto_id,
                message_id=msg.id,
                last_sent_at=iso(agora),
                next_send_at=iso(proximo),
            )

            registrar_auto_message_log(
                auto_id,
                interaction.guild.id,
                canal.id,
                "created",
                msg.id,
                "Primeiro envio pelo /automsg.",
            )

            await interaction.followup.send(
                "✅ **AutoMensagem criada!**\n\n"
                f"🆔 ID: `{auto_id}`\n"
                f"📢 Canal: {canal.mention}\n"
                f"⏱️ Intervalo: **{intervalo} dia(s)**\n"
                "🖼️ Banner: **ativado**\n"
                "💜 Visual: **LN Premium**\n"
                "🔗 Convite: **detectado automaticamente**",
                ephemeral=True,
            )

        except Exception as erro:

            print(
                f"[AUTOMSG] Erro criando: {erro}",
                flush=True,
            )

            await interaction.followup.send(
                f"❌ Erro ao criar AutoMensagem:\n`{erro}`",
                ephemeral=True,
            )

    # =========================================================
    # /AUTOMSG_DELETAR
    # =========================================================

    @app_commands.command(
        name="automsg_deletar",
        description="Exclui uma AutoMensagem e apaga sua mensagem do Discord.",
    )
    @app_commands.describe(
        id="ID da AutoMensagem que deseja excluir.",
    )
    async def automsg_deletar(
        self,
        interaction: discord.Interaction,
        id: int,
    ):

        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Este comando só pode ser usado em um servidor.",
                ephemeral=True,
            )
            return

        if not pode_controlar_evelly(
            interaction.user
        ):
            await interaction.response.send_message(
                "❌ Você não possui permissão para excluir AutoMensagens.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(
            ephemeral=True
        )

        item = pegar_auto_message(
            id,
            interaction.guild.id,
        )

        if not item:
            await interaction.followup.send(
                f"❌ A AutoMensagem `{id}` não foi encontrada neste servidor.",
                ephemeral=True,
            )
            return

        message_id = item.get(
            "message_id"
        )

        channel_id = item.get(
            "channel_id"
        )

        mensagem_apagada = False
        aviso_apagar = ""

        # -----------------------------------------------------
        # APAGAR A MENSAGEM DO DISCORD
        # -----------------------------------------------------

        if message_id and channel_id:

            try:

                channel = interaction.guild.get_channel(
                    int(channel_id)
                )

                if channel is None:
                    channel = await self.bot.fetch_channel(
                        int(channel_id)
                    )

                mensagem_discord = await channel.fetch_message(
                    int(message_id)
                )

                await mensagem_discord.delete()

                mensagem_apagada = True

            except discord.NotFound:
                # A mensagem já não existe.
                mensagem_apagada = True

            except discord.Forbidden:
                aviso_apagar = (
                    "⚠️ Não consegui apagar a mensagem do Discord "
                    "por falta de permissão."
                )

            except Exception as erro:
                aviso_apagar = (
                    f"⚠️ Não consegui apagar a mensagem do Discord: "
                    f"{erro}"
                )

        # -----------------------------------------------------
        # EXCLUIR AUTOMATIZAÇÃO DO SUPABASE
        # -----------------------------------------------------

        excluida = excluir_auto_message(
            id,
            interaction.guild.id,
        )

        if not excluida:

            await interaction.followup.send(
                "❌ Não consegui excluir a AutoMensagem do Supabase.\n\n"
                "A mensagem do Discord não foi alterada pela Evelly.",
                ephemeral=True,
            )
            return

        registrar_auto_message_log(
            id,
            interaction.guild.id,
            channel_id,
            "deleted",
            message_id,
            "AutoMensagem excluída pelo comando /automsg_deletar.",
        )

        if aviso_apagar:

            await interaction.followup.send(
                f"🗑️ AutoMensagem `{id}` removida do sistema.\n\n"
                f"{aviso_apagar}",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            f"🗑️ **AutoMensagem `{id}` excluída com sucesso!**\n\n"
            + (
                "💬 A mensagem também foi apagada do Discord."
                if mensagem_apagada
                else "💬 Não havia mensagem vinculada para apagar."
            ),
            ephemeral=True,
        )

    # =========================================================
    # PROCESSADOR AUTOMÁTICO
    # =========================================================

    @tasks.loop(seconds=PROCESS_INTERVAL_SECONDS)
    async def processar_automsg(self):

        try:

            registros = (
                pegar_auto_messages_pendentes()
            )

            for item in registros:

                try:

                    if not item.get("enabled"):
                        continue

                    guild = self.bot.get_guild(
                        int(item.get("guild_id"))
                    )

                    if guild is None:
                        continue

                    vencimento = (
                        parse_dt(
                            item.get("next_send_at")
                        )
                        or now_utc()
                    )

                    if vencimento > now_utc():
                        continue

                    intervalo = max(
                        1,
                        int(
                            item.get(
                                "interval_days"
                            )
                            or 1
                        ),
                    )

                    proximo = (
                        now_utc()
                        + timedelta(
                            days=intervalo
                        )
                    )

                    atualizar_auto_message(
                        item.get("id"),
                        next_send_at=iso(
                            proximo
                        ),
                    )

                    msg, ok, detalhes = (
                        await self.enviar_automacao(
                            guild,
                            item,
                        )
                    )

                    if not ok:

                        atualizar_auto_message(
                            item.get("id"),
                            next_send_at=iso(
                                now_utc()
                                + timedelta(
                                    minutes=5
                                )
                            ),
                        )

                        registrar_auto_message_log(
                            item.get("id"),
                            guild.id,
                            item.get("channel_id"),
                            "error",
                            item.get("message_id"),
                            detalhes,
                        )

                        continue

                    atualizar_auto_message(
                        item.get("id"),
                        message_id=msg.id,
                        last_sent_at=iso(
                            now_utc()
                        ),
                        next_send_at=iso(
                            proximo
                        ),
                    )

                    registrar_auto_message_log(
                        item.get("id"),
                        guild.id,
                        item.get("channel_id"),
                        "sent",
                        msg.id,
                        "Envio automático.",
                    )

                except Exception as erro:

                    print(
                        f"[AUTOMSG] Erro no item "
                        f"{item.get('id')}: {erro}",
                        flush=True,
                    )

        except Exception as erro:

            print(
                f"[AUTOMSG] Erro no processador: {erro}",
                flush=True,
            )

    @processar_automsg.before_loop
    async def antes_processar(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(
        AutoMensagem(bot)
    )
