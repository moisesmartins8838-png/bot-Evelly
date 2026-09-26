import json
from pathlib import Path
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from database.database import supabase
from cogs.permissoes import pode_controlar_evelly


PURPLE = 0x8E44AD
UPDATES_FILE = Path(__file__).resolve().parent.parent / "updates.json"


def carregar_update():
    """Carrega a versão/changelog que está no repositório."""
    try:
        if not UPDATES_FILE.exists():
            return None

        with UPDATES_FILE.open("r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)

        if not dados.get("version"):
            return None

        return dados
    except Exception as erro:
        print(f"[UPDATES] Erro lendo updates.json: {erro}", flush=True)
        return None


def buscar_canal_configurado(guild_id):
    try:
        resposta = (
            supabase.table("evelly_update_config")
            .select("channel_id")
            .eq("guild_id", int(guild_id))
            .limit(1)
            .execute()
        )

        if not resposta.data:
            return None

        valor = resposta.data[0].get("channel_id")
        return int(valor) if valor else None
    except Exception as erro:
        print(f"[UPDATES] Erro buscando canal: {erro}", flush=True)
        return None


def salvar_canal(guild_id, channel_id):
    try:
        supabase.table("evelly_update_config").upsert(
            {
                "guild_id": int(guild_id),
                "channel_id": int(channel_id),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="guild_id",
        ).execute()
        return True
    except Exception as erro:
        print(f"[UPDATES] Erro salvando canal: {erro}", flush=True)
        return False


def remover_canal(guild_id):
    try:
        supabase.table("evelly_update_config").delete().eq(
            "guild_id", int(guild_id)
        ).execute()
        return True
    except Exception as erro:
        print(f"[UPDATES] Erro removendo canal: {erro}", flush=True)
        return False


def ja_anunciada(guild_id, version):
    try:
        resposta = (
            supabase.table("evelly_update_history")
            .select("id")
            .eq("guild_id", int(guild_id))
            .eq("version", str(version))
            .limit(1)
            .execute()
        )
        return bool(resposta.data)
    except Exception as erro:
        print(f"[UPDATES] Erro verificando histórico: {erro}", flush=True)
        return False


def registrar_anuncio(guild_id, channel_id, version, message_id):
    try:
        supabase.table("evelly_update_history").insert(
            {
                "guild_id": int(guild_id),
                "channel_id": int(channel_id),
                "version": str(version),
                "message_id": int(message_id),
                "announced_at": datetime.now(timezone.utc).isoformat(),
            }
        ).execute()
        return True
    except Exception as erro:
        print(f"[UPDATES] Erro registrando histórico: {erro}", flush=True)
        return False


def montar_embed(dados):
    version = str(dados.get("version", "0.0.0"))
    title = dados.get("title") or "Nova atualização da Evelly"
    description = dados.get("description") or (
        "A Evelly recebeu uma nova atualização."
    )
    date = dados.get("date")

    embed = discord.Embed(
        title=f"🌸 EVELLY FOI ATUALIZADA!",
        description=(
            f"**{title}**\n\n"
            f"{description}"
        ),
        color=PURPLE,
        timestamp=datetime.now(timezone.utc),
    )

    embed.add_field(name="📦 Versão", value=f"`v{version}`", inline=True)

    if date:
        embed.add_field(name="📅 Data", value=str(date), inline=True)

    sections = [
        ("✨ Novidades", dados.get("new", [])),
        ("🐛 Correções", dados.get("fixed", [])),
        ("⚙️ Melhorias", dados.get("improved", [])),
        ("🗑️ Removido", dados.get("removed", [])),
        ("🔐 Segurança", dados.get("security", [])),
    ]

    for nome, itens in sections:
        if not itens:
            continue

        texto = "\n".join(f"• {item}" for item in itens)

        # Discord permite no máximo 1024 caracteres por field.
        if len(texto) > 1000:
            texto = texto[:997] + "..."

        embed.add_field(name=nome, value=texto, inline=False)

    embed.set_footer(text=f"Evelly • v{version}")

    return embed


class Atualizacoes(commands.Cog):
    """Sistema de changelog e anúncios de atualizações da Evelly."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _pode_configurar(self, interaction: discord.Interaction):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return False

        try:
            return pode_controlar_evelly(interaction.user)
        except Exception:
            return interaction.user.guild_permissions.manage_guild

    async def anunciar_atualizacao(
        self,
        guild: discord.Guild,
        *,
        forcar=False,
    ):
        dados = carregar_update()

        if not dados:
            print("[UPDATES] updates.json não encontrado ou inválido.", flush=True)
            return False

        version = str(dados["version"])
        channel_id = buscar_canal_configurado(guild.id)

        if not channel_id:
            print(
                f"[UPDATES] {guild.name}: nenhum canal de atualizações configurado.",
                flush=True,
            )
            return False

        if not forcar and ja_anunciada(guild.id, version):
            return False

        channel = guild.get_channel(channel_id)

        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except Exception as erro:
                print(
                    f"[UPDATES] Canal não encontrado em {guild.name}: {erro}",
                    flush=True,
                )
                return False

        if not isinstance(channel, discord.TextChannel):
            print(
                f"[UPDATES] Canal configurado não é um canal de texto: "
                f"{guild.name} / {channel_id}",
                flush=True,
            )
            return False

        try:
            mensagem = await channel.send(
                embed=montar_embed(dados),
                allowed_mentions=discord.AllowedMentions.none(),
            )

            if not forcar:
                registrar_anuncio(
                    guild.id,
                    channel.id,
                    version,
                    mensagem.id,
                )

            print(
                f"[UPDATES] Atualização v{version} anunciada em "
                f"{guild.name} / #{channel.name}",
                flush=True,
            )

            return True

        except discord.Forbidden:
            print(
                f"[UPDATES] Sem permissão para enviar no canal "
                f"{guild.name} / {channel_id}.",
                flush=True,
            )
            return False

        except discord.HTTPException as erro:
            print(f"[UPDATES] Erro Discord ao anunciar: {erro}", flush=True)
            return False

    @app_commands.command(
        name="evelly_atualizacoes",
        description="Configura o canal que receberá as atualizações da Evelly.",
    )
    @app_commands.describe(canal="Canal onde a Evelly enviará os changelogs.")
    async def evelly_atualizacoes(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel,
    ):
        if not await self._pode_configurar(interaction):
            await interaction.response.send_message(
                "❌ Você não tem permissão para configurar a Evelly.",
                ephemeral=True,
            )
            return

        if not salvar_canal(interaction.guild.id, canal.id):
            await interaction.response.send_message(
                "❌ Não consegui salvar o canal no Supabase.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"✅ Canal de atualizações configurado para {canal.mention}.\n\n"
            "A Evelly enviará automaticamente novas versões nesse canal.",
            ephemeral=True,
        )

    @app_commands.command(
        name="evelly_atualizacoes_teste",
        description="Envia a atualização atual da Evelly para testar o sistema.",
    )
    async def evelly_atualizacoes_teste(
        self,
        interaction: discord.Interaction,
    ):
        if not await self._pode_configurar(interaction):
            await interaction.response.send_message(
                "❌ Você não tem permissão para configurar a Evelly.",
                ephemeral=True,
            )
            return

        dados = carregar_update()

        if not dados:
            await interaction.response.send_message(
                "❌ Não encontrei um `updates.json` válido.",
                ephemeral=True,
            )
            return

        channel_id = buscar_canal_configurado(interaction.guild.id)

        if not channel_id:
            await interaction.response.send_message(
                "❌ Nenhum canal de atualizações foi configurado.",
                ephemeral=True,
            )
            return

        channel = interaction.guild.get_channel(channel_id)

        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ O canal configurado não está disponível.",
                ephemeral=True,
            )
            return

        try:
            await channel.send(
                embed=montar_embed(dados),
                allowed_mentions=discord.AllowedMentions.none(),
            )

            await interaction.response.send_message(
                f"✅ Teste enviado em {channel.mention}.",
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ A Evelly não tem permissão para enviar mensagens nesse canal.",
                ephemeral=True,
            )

    @app_commands.command(
        name="evelly_atualizacoes_remover",
        description="Remove o canal de atualizações configurado.",
    )
    async def evelly_atualizacoes_remover(
        self,
        interaction: discord.Interaction,
    ):
        if not await self._pode_configurar(interaction):
            await interaction.response.send_message(
                "❌ Você não tem permissão para configurar a Evelly.",
                ephemeral=True,
            )
            return

        if remover_canal(interaction.guild.id):
            await interaction.response.send_message(
                "✅ Canal de atualizações removido.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "❌ Não consegui remover a configuração.",
                ephemeral=True,
            )

    @app_commands.command(
        name="evelly_atualizacoes_status",
        description="Mostra a configuração atual das atualizações da Evelly.",
    )
    async def evelly_atualizacoes_status(
        self,
        interaction: discord.Interaction,
    ):
        if not await self._pode_configurar(interaction):
            await interaction.response.send_message(
                "❌ Você não tem permissão para visualizar esta configuração.",
                ephemeral=True,
            )
            return

        dados = carregar_update()
        channel_id = buscar_canal_configurado(interaction.guild.id)

        canal_texto = (
            f"<#{channel_id}>" if channel_id else "Não configurado"
        )
        versao = f"v{dados['version']}" if dados else "indisponível"

        await interaction.response.send_message(
            "🌸 **Configuração de Atualizações da Evelly**\n\n"
            f"📦 Versão atual: `{versao}`\n"
            f"📢 Canal: {canal_texto}",
            ephemeral=True,
        )

    async def cog_load(self):
        """Ao iniciar, verifica se existe uma nova versão para anunciar."""
        print("[UPDATES] Sistema de atualizações carregado.", flush=True)

    @commands.Cog.listener()
    async def on_ready(self):
        # on_ready pode ocorrer mais de uma vez; o histórico no Supabase
        # impede duplicações por versão.
        for guild in list(self.bot.guilds):
            try:
                await self.anunciar_atualizacao(guild)
            except Exception as erro:
                print(
                    f"[UPDATES] Erro processando {guild.name}: {erro}",
                    flush=True,
                )


async def setup(bot: commands.Bot):
    await bot.add_cog(Atualizacoes(bot))
