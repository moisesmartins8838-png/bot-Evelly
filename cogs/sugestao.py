from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from database.database import supabase
from cogs.permissoes import pode_controlar_evelly


PURPLE = 0x8E44AD


def get_cfg(guild_id):
    try:
        r = (
            supabase.table("evelly_suggestion_config")
            .select("*")
            .eq("guild_id", guild_id)
            .limit(1)
            .execute()
        )
        return r.data[0] if r.data else None
    except Exception as e:
        print(f"[SUGESTAO] Config error: {e}", flush=True)
        return None


def save_cfg(guild_id, channel_id, staff_role_id=None):
    try:
        supabase.table("evelly_suggestion_config").upsert({
            "guild_id": int(guild_id),
            "channel_id": int(channel_id),
            "staff_role_id": int(staff_role_id) if staff_role_id else None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, on_conflict="guild_id").execute()
        return True
    except Exception as e:
        print(f"[SUGESTAO] Save error: {e}", flush=True)
        return False


def create_suggestion(guild_id, channel_id, message_id, user_id, title, description):
    try:
        r = supabase.table("evelly_suggestions").insert({
            "guild_id": int(guild_id),
            "channel_id": int(channel_id),
            "message_id": int(message_id),
            "user_id": int(user_id),
            "title": title,
            "description": description,
            "status": "pending",
        }).execute()
        return r.data[0] if r.data else None
    except Exception as e:
        print(f"[SUGESTAO] Create error: {e}", flush=True)
        return None


def update_suggestion(suggestion_id, status):
    try:
        r = (
            supabase.table("evelly_suggestions")
            .update({
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", int(suggestion_id))
            .execute()
        )
        return bool(r.data)
    except Exception as e:
        print(f"[SUGESTAO] Update error: {e}", flush=True)
        return False


class SuggestionModal(discord.ui.Modal, title="💡 Nova sugestão"):
    titulo = discord.ui.TextInput(
        label="Título",
        placeholder="Ex.: Criar canal de música",
        max_length=100,
    )

    descricao = discord.ui.TextInput(
        label="Descrição",
        placeholder="Explique sua sugestão...",
        style=discord.TextStyle.paragraph,
        max_length=1500,
    )

    async def on_submit(self, interaction: discord.Interaction):
        cfg = get_cfg(interaction.guild.id)

        if not cfg:
            await interaction.response.send_message(
                "❌ O sistema de sugestões ainda não foi configurado.",
                ephemeral=True,
            )
            return

        canal = interaction.guild.get_channel(
            int(cfg["channel_id"])
        )

        if not isinstance(canal, discord.TextChannel):
            await interaction.response.send_message(
                "❌ O canal de sugestões não existe mais.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=f"💡 {self.titulo.value}",
            description=self.descricao.value,
            color=PURPLE,
        )
        embed.add_field(
            name="👤 Autor",
            value=interaction.user.mention,
            inline=True,
        )
        embed.add_field(
            name="📌 Status",
            value="🟡 Em análise",
            inline=True,
        )
        embed.set_footer(
            text="Evelly • Sistema de Sugestões"
        )

        mensagem = await canal.send(embed=embed)

        await mensagem.add_reaction("👍")
        await mensagem.add_reaction("👎")

        registro = create_suggestion(
            interaction.guild.id,
            canal.id,
            mensagem.id,
            interaction.user.id,
            self.titulo.value,
            self.descricao.value,
        )

        if not registro:
            await mensagem.delete()
            await interaction.response.send_message(
                "❌ Não consegui salvar sua sugestão.",
                ephemeral=True,
            )
            return

        # O ID só existe depois do INSERT. Por isso a view de análise
        # é anexada ao final, usando o ID salvo no Supabase.
        await mensagem.edit(
            view=SuggestionReviewView(registro["id"])
        )

        await interaction.response.send_message(
            "✅ **Sugestão enviada!**\n"
            f"Sua sugestão recebeu o ID `{registro['id']}`.",
            ephemeral=True,
        )


class SuggestionReviewView(discord.ui.View):
    def __init__(self, suggestion_id):
        super().__init__(timeout=None)
        self.suggestion_id = suggestion_id

    async def change_status(self, interaction, status, label):
        cfg = get_cfg(interaction.guild.id) if interaction.guild else None
        staff_role_id = cfg.get("staff_role_id") if cfg else None

        autorizado = pode_controlar_evelly(interaction.user)

        if (
            not autorizado
            and staff_role_id
            and isinstance(interaction.user, discord.Member)
        ):
            autorizado = any(
                role.id == int(staff_role_id)
                for role in interaction.user.roles
            )

        if not autorizado:
            await interaction.response.send_message(
                "❌ Apenas a equipe autorizada pode alterar sugestões.",
                ephemeral=True,
            )
            return

        ok = update_suggestion(
            self.suggestion_id,
            status,
        )

        if not ok:
            await interaction.response.send_message(
                "❌ Não consegui atualizar a sugestão.",
                ephemeral=True,
            )
            return

        try:
            embed = interaction.message.embeds[0]
            embed.set_field_at(
                1,
                name="📌 Status",
                value=label,
                inline=True,
            )
            await interaction.message.edit(
                embed=embed,
                view=self,
            )
        except Exception:
            pass

        await interaction.response.send_message(
            f"✅ Sugestão `{self.suggestion_id}` atualizada para **{label}**.",
            ephemeral=True,
        )

    @discord.ui.button(
        label="Aprovar",
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id="evelly_suggestion_approve",
    )
    async def aprovar(self, interaction, button):
        await self.change_status(
            interaction,
            "approved",
            "🟢 Aprovada",
        )

    @discord.ui.button(
        label="Recusar",
        emoji="❌",
        style=discord.ButtonStyle.danger,
        custom_id="evelly_suggestion_reject",
    )
    async def recusar(self, interaction, button):
        await self.change_status(
            interaction,
            "rejected",
            "🔴 Recusada",
        )

    @discord.ui.button(
        label="Implementada",
        emoji="🚀",
        style=discord.ButtonStyle.primary,
        custom_id="evelly_suggestion_implemented",
    )
    async def implementada(self, interaction, button):
        await self.change_status(
            interaction,
            "implemented",
            "💜 Implementada",
        )


class SuggestionPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Enviar sugestão",
        emoji="💡",
        style=discord.ButtonStyle.primary,
        custom_id="evelly_suggestion_open",
    )
    async def abrir(self, interaction, button):
        await interaction.response.send_modal(
            SuggestionModal()
        )


class Sugestao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    sugestao = app_commands.Group(
        name="sugestao",
        description="Sistema de sugestões da Evelly.",
    )

    @sugestao.command(
        name="configurar",
        description="Configura o canal e o cargo que analisa sugestões.",
    )
    @app_commands.describe(
        canal="Canal onde as sugestões serão publicadas.",
        equipe="Cargo que poderá analisar as sugestões.",
    )
    async def configurar(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel,
        equipe: discord.Role | None = None,
    ):
        if not pode_controlar_evelly(interaction.user):
            await interaction.response.send_message(
                "❌ Você não possui permissão para configurar sugestões.",
                ephemeral=True,
            )
            return

        if not save_cfg(
            interaction.guild.id,
            canal.id,
            equipe.id if equipe else None,
        ):
            await interaction.response.send_message(
                "❌ Não consegui salvar a configuração.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "✅ **Sugestões configuradas!**\n\n"
            f"📢 Canal: {canal.mention}\n"
            f"🛡️ Equipe: {equipe.mention if equipe else 'Administradores da Evelly'}\n\n"
            "Agora use `/sugestao painel` para publicar o painel.",
            ephemeral=True,
        )

    @sugestao.command(
        name="painel",
        description="Publica o painel para os membros enviarem sugestões.",
    )
    @app_commands.describe(
        canal="Canal onde o painel será publicado.",
    )
    async def painel(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel,
    ):
        if not pode_controlar_evelly(interaction.user):
            await interaction.response.send_message(
                "❌ Você não possui permissão para publicar o painel.",
                ephemeral=True,
            )
            return

        cfg = get_cfg(interaction.guild.id)

        if not cfg:
            await interaction.response.send_message(
                "❌ Configure primeiro com `/sugestao configurar`.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="💡 Sugestões da comunidade",
            description=(
                "Tem uma ideia para melhorar o servidor?\n\n"
                "Clique no botão abaixo e envie sua sugestão.\n\n"
                "👍 A comunidade poderá votar.\n"
                "🛡️ A equipe poderá analisar.\n"
                "📌 O status ficará registrado."
            ),
            color=PURPLE,
        )
        embed.set_footer(text="Evelly • Sugestões")

        await canal.send(
            embed=embed,
            view=SuggestionPanelView(),
        )

        await interaction.response.send_message(
            f"✅ Painel de sugestões publicado em {canal.mention}.",
            ephemeral=True,
        )

    async def cog_load(self):
        self.bot.add_view(SuggestionPanelView())

        # Restaura os botões de análise das sugestões já existentes.
        # Isso faz os botões continuarem funcionando após reinícios.
        try:
            result = (
                supabase.table("evelly_suggestions")
                .select("id, message_id")
                .execute()
            )

            for row in result.data or []:
                message_id = row.get("message_id")
                suggestion_id = row.get("id")

                if message_id and suggestion_id:
                    self.bot.add_view(
                        SuggestionReviewView(suggestion_id),
                        message_id=int(message_id),
                    )

            print(
                f"💡 Views de sugestões restauradas: {len(result.data or [])}",
                flush=True,
            )
        except Exception as e:
            print(
                f"[SUGESTAO] Erro ao restaurar views: {e}",
                flush=True,
            )


async def setup(bot):
    await bot.add_cog(Sugestao(bot))
    print("💡 cogs.sugestao carregado com sucesso", flush=True)
