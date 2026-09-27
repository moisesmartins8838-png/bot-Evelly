import asyncio
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from database.database import supabase
from cogs.permissoes import pode_controlar_evelly

DEFAULT_COLOR = 0x8E44AD


def get_config(guild_id: int, channel_id: int):
    result = (
        supabase.table("evelly_sticky")
        .select("*")
        .eq("guild_id", str(guild_id))
        .eq("channel_id", str(channel_id))
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return rows[0] if rows else None


def get_guild_configs(guild_id: int):
    result = (
        supabase.table("evelly_sticky")
        .select("*")
        .eq("guild_id", str(guild_id))
        .execute()
    )
    return result.data or []


class Sticky(commands.GroupCog, group_name="sticky", group_description="Gerencia mensagens fixas que ficam sempre no final do canal."):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.locks: dict[int, asyncio.Lock] = {}

        print("📌 Sistema Sticky carregado com sucesso.", flush=True)

    def _get_lock(self, channel_id: int) -> asyncio.Lock:
        if channel_id not in self.locks:
            self.locks[channel_id] = asyncio.Lock()
        return self.locks[channel_id]

    @staticmethod
    def build_embed(config: dict) -> discord.Embed:
        title = config.get("title") or "📌 Mensagem fixa"
        description = config.get("description") or ""
        color_value = config.get("color") or DEFAULT_COLOR

        try:
            color_value = int(color_value)
        except (TypeError, ValueError):
            color_value = DEFAULT_COLOR

        return discord.Embed(
            title=title,
            description=description,
            color=discord.Color(color_value),
        )

    async def send_sticky(
        self,
        channel: discord.TextChannel,
        config: dict,
        old_message_id: Optional[int] = None,
    ):
        lock = self._get_lock(channel.id)

        async with lock:
            # Remove a mensagem sticky anterior.
            if old_message_id:
                try:
                    old_message = await channel.fetch_message(int(old_message_id))
                    await old_message.delete()
                except discord.NotFound:
                    pass
                except discord.Forbidden:
                    print(
                        f"[STICKY] Sem permissão para apagar a mensagem anterior em #{channel.name}.",
                        flush=True,
                    )
                except discord.HTTPException as e:
                    print(
                        f"[STICKY] Erro apagando mensagem anterior: {e}",
                        flush=True,
                    )

            embed = self.build_embed(config)

            try:
                new_message = await channel.send(
                    embed=embed,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except discord.Forbidden:
                print(
                    f"[STICKY] Sem permissão para enviar mensagem em #{channel.name}.",
                    flush=True,
                )
                return None
            except discord.HTTPException as e:
                print(
                    f"[STICKY] Erro enviando mensagem em #{channel.name}: {e}",
                    flush=True,
                )
                return None

            try:
                (
                    supabase.table("evelly_sticky")
                    .update(
                        {
                            "message_id": str(new_message.id),
                            "updated_at": "now()",
                        }
                    )
                    .eq("id", config["id"])
                    .execute()
                )
            except Exception as e:
                print(
                    f"[STICKY] Erro salvando message_id no Supabase: {e}",
                    flush=True,
                )

            return new_message

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if not message.guild:
            return

        if not isinstance(message.channel, discord.TextChannel):
            return

        try:
            config = get_config(message.guild.id, message.channel.id)
        except Exception as e:
            print(f"[STICKY] Erro consultando configuração: {e}", flush=True)
            return

        if not config:
            return

        await self.send_sticky(
            message.channel,
            config,
            config.get("message_id"),
        )

    @app_commands.command(
        name="configurar",
        description="Configura uma mensagem fixa para ficar sempre no final do canal.",
    )
    @app_commands.describe(
        canal="Canal onde a mensagem fixa ficará.",
        titulo="Título da mensagem fixa.",
        mensagem="Texto da mensagem fixa.",
        cor="Cor hexadecimal, por exemplo: #8E44AD.",
    )
    async def configurar(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel,
        titulo: str,
        mensagem: str,
        cor: Optional[str] = None,
    ):
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ Este comando só pode ser usado em um servidor.",
                ephemeral=True,
            )
            return

        if not pode_controlar_evelly(interaction.user):
            await interaction.response.send_message(
                "❌ Você não tem permissão para controlar a Evelly.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        color_value = DEFAULT_COLOR

        if cor:
            texto_cor = cor.strip().replace("#", "").replace("0x", "")
            try:
                color_value = int(texto_cor, 16)
                if not 0 <= color_value <= 0xFFFFFF:
                    raise ValueError
            except ValueError:
                await interaction.followup.send(
                    "❌ Cor inválida. Use algo como `#8E44AD`.",
                    ephemeral=True,
                )
                return

        try:
            existing = get_config(interaction.guild.id, canal.id)

            data = {
                "guild_id": str(interaction.guild.id),
                "channel_id": str(canal.id),
                "title": titulo,
                "description": mensagem,
                "color": color_value,
                "updated_at": "now()",
            }

            if existing:
                old_message_id = existing.get("message_id")

                result = (
                    supabase.table("evelly_sticky")
                    .update(data)
                    .eq("id", existing["id"])
                    .execute()
                )
                config = (result.data or [existing])[0]

                new_message = await self.send_sticky(
                    canal,
                    config,
                    old_message_id,
                )
                action = "atualizada"
            else:
                data["created_at"] = "now()"

                result = (
                    supabase.table("evelly_sticky")
                    .insert(data)
                    .execute()
                )

                config = (result.data or [None])[0]

                if not config:
                    raise RuntimeError(
                        "O Supabase não retornou a configuração criada."
                    )

                new_message = await self.send_sticky(canal, config)
                action = "configurada"

            if not new_message:
                await interaction.followup.send(
                    "⚠️ A configuração foi salva, mas não consegui enviar a mensagem. "
                    "Verifique as permissões da Evelly no canal.",
                    ephemeral=True,
                )
                return

            embed = discord.Embed(
                title="📌 Sticky configurado",
                description=(
                    f"**Canal:** {canal.mention}\n"
                    f"**Título:** {titulo}\n"
                    f"**Status:** {action}"
                ),
                color=discord.Color(color_value),
            )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            print(f"[STICKY] Erro no /sticky configurar: {e}", flush=True)

            await interaction.followup.send(
                f"❌ Não foi possível configurar o Sticky.\n"
                f"`{e}`",
                ephemeral=True,
            )

    @app_commands.command(
        name="remover",
        description="Remove a mensagem fixa de um canal.",
    )
    @app_commands.describe(
        canal="Canal que terá o Sticky removido.",
    )
    async def remover(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel,
    ):
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ Este comando só pode ser usado em um servidor.",
                ephemeral=True,
            )
            return

        if not pode_controlar_evelly(interaction.user):
            await interaction.response.send_message(
                "❌ Você não tem permissão para controlar a Evelly.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            config = get_config(interaction.guild.id, canal.id)

            if not config:
                await interaction.followup.send(
                    "❌ Não existe Sticky configurado nesse canal.",
                    ephemeral=True,
                )
                return

            message_id = config.get("message_id")

            if message_id:
                try:
                    message = await canal.fetch_message(int(message_id))
                    await message.delete()
                except discord.NotFound:
                    pass
                except discord.Forbidden:
                    await interaction.followup.send(
                        "❌ Não tenho permissão para apagar a mensagem Sticky nesse canal.",
                        ephemeral=True,
                    )
                    return

            supabase.table("evelly_sticky").delete().eq(
                "id", config["id"]
            ).execute()

            await interaction.followup.send(
                f"✅ Sticky removido de {canal.mention}.",
                ephemeral=True,
            )

        except Exception as e:
            print(f"[STICKY] Erro no /sticky remover: {e}", flush=True)

            await interaction.followup.send(
                f"❌ Não foi possível remover o Sticky.\n`{e}`",
                ephemeral=True,
            )

    @app_commands.command(
        name="status",
        description="Mostra os Stickys configurados neste servidor.",
    )
    async def status(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ Este comando só pode ser usado em um servidor.",
                ephemeral=True,
            )
            return

        if not pode_controlar_evelly(interaction.user):
            await interaction.response.send_message(
                "❌ Você não tem permissão para controlar a Evelly.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            configs = get_guild_configs(interaction.guild.id)

            if not configs:
                await interaction.followup.send(
                    "📌 Nenhum Sticky configurado neste servidor.",
                    ephemeral=True,
                )
                return

            embed = discord.Embed(
                title="📌 Stickys configurados",
                color=discord.Color(DEFAULT_COLOR),
            )

            linhas = []

            for config in configs:
                channel = interaction.guild.get_channel(
                    int(config["channel_id"])
                )

                canal_texto = (
                    channel.mention
                    if channel
                    else f"`{config['channel_id']}`"
                )

                linhas.append(
                    f"• {canal_texto} — **{config.get('title') or 'Sem título'}**"
                )

            embed.description = "\n".join(linhas)

            await interaction.followup.send(
                embed=embed,
                ephemeral=True,
            )

        except Exception as e:
            print(f"[STICKY] Erro no /sticky status: {e}", flush=True)

            await interaction.followup.send(
                f"❌ Não foi possível consultar os Stickys.\n`{e}`",
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Sticky(bot))
