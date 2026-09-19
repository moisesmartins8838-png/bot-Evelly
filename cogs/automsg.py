import os
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

from database.database import (
    criar_auto_message,
    listar_auto_messages,
    pegar_auto_message,
    pegar_auto_messages_pendentes,
    atualizar_auto_message,
    excluir_auto_message,
    registrar_auto_message_log,
)

load_dotenv()

DEFAULT_COLOR = 0x9B59B6
INVITE_MARKER = "__EVELLY_AUTOMSG_INVITE__"
PROCESS_INTERVAL_SECONDS = 60


def is_owner(user: discord.abc.User) -> bool:
    try:
        return user.id == int(os.getenv("OWNER_ID", "0"))
    except (TypeError, ValueError):
        return False


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def parse_dt(value) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        value = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(value)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def parse_color(value: str | None) -> int:
    value = (value or "").strip().replace("#", "")
    if not value:
        return DEFAULT_COLOR
    if not re.fullmatch(r"[0-9a-fA-F]{6}", value):
        raise ValueError("A cor precisa estar no formato #RRGGBB.")
    return int(value, 16)


def replace_vars(text: str | None, guild: discord.Guild, channel=None) -> str:
    if not text:
        return ""
    now = now_utc()
    values = {
        "{server}": guild.name,
        "{servidor}": guild.name,
        "{member_count}": str(guild.member_count or 0),
        "{membros}": str(guild.member_count or 0),
        "{data}": now.strftime("%d/%m/%Y"),
        "{hora}": now.strftime("%H:%M"),
        "{id}": str(guild.id),
    }
    if channel:
        values.update({
            "{channel}": channel.name,
            "{canal}": channel.name,
            "{channel_id}": str(channel.id),
            "{canal_id}": str(channel.id),
        })
    for key, value in values.items():
        text = text.replace(key, value)
    return text


def pack_content(message: str, invite_url: str) -> str:
    if not invite_url:
        return message or ""
    payload = {
        "message": message or "",
        "invite_url": invite_url.strip(),
    }
    return INVITE_MARKER + json.dumps(payload, ensure_ascii=False)


def unpack_content(content: str | None) -> tuple[str, str]:
    content = content or ""
    if not content.startswith(INVITE_MARKER):
        return content, ""
    try:
        payload = json.loads(content[len(INVITE_MARKER):])
        return payload.get("message", ""), payload.get("invite_url", "")
    except Exception:
        return "", ""


def extract_invite(url: str | None) -> str:
    if not url:
        return ""
    url = url.strip()
    match = re.search(r"(?:https?://)?(?:www\.)?(?:discord\.gg|discord\.com/invite)/([A-Za-z0-9-]+)", url, re.I)
    return f"https://discord.gg/{match.group(1)}" if match else ""


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit - 3] + "..."


def make_standard_embed(guild: discord.Guild, channel, title: str, description: str, color: int):
    if not title and not description:
        return None
    embed = discord.Embed(
        title=truncate(title, 256) if title else None,
        description=truncate(description, 4096) if description else None,
        color=color,
        timestamp=now_utc(),
    )
    return embed


async def make_invite_embed(bot: commands.Bot, invite_url: str, fallback_description: str, color: int):
    invite_url = extract_invite(invite_url)
    if not invite_url:
        return None, None, ""

    try:
        invite = await bot.fetch_invite(invite_url, with_counts=True)
    except discord.NotFound:
        return None, None, "❌ O convite do Discord é inválido ou expirou."
    except discord.HTTPException as exc:
        return None, None, f"❌ Não foi possível consultar o convite: {exc}"
    except discord.Forbidden:
        return None, None, "❌ O Discord recusou a consulta desse convite."

    partial = invite.guild
    name = getattr(partial, "name", None) or "Servidor Discord"
    icon_url = None
    icon = getattr(partial, "icon", None)
    if icon:
        try:
            icon_url = icon.url
        except Exception:
            pass

    online = getattr(invite, "approximate_presence_count", None)
    members = getattr(invite, "approximate_member_count", None)

    description = fallback_description.strip() if fallback_description else ""
    if not description:
        description = "Entre agora e conheça a comunidade!"

    embed = discord.Embed(
        title=f"🔗 {name}",
        description=truncate(description, 4096),
        color=color,
        timestamp=now_utc(),
    )

    if icon_url:
        embed.set_thumbnail(url=icon_url)

    stats = []
    if online is not None:
        stats.append(f"🟢 {online:,} online".replace(",", "."))
    if members is not None:
        stats.append(f"👥 {members:,} membros".replace(",", "."))
    if stats:
        embed.add_field(name="Comunidade", value=" • ".join(stats), inline=False)

    embed.set_footer(text="Evelly • Convite do servidor")
    return embed, invite_url, ""


class AutoMsgContentModal(discord.ui.Modal, title="Conteúdo da AutoMensagem"):
    titulo = discord.ui.TextInput(label="Título do Embed", max_length=256, required=False)
    descricao = discord.ui.TextInput(label="Descrição do Embed", style=discord.TextStyle.paragraph, max_length=4000, required=False)
    mensagem = discord.ui.TextInput(label="Mensagem de texto", style=discord.TextStyle.paragraph, max_length=2000, required=False)
    convite = discord.ui.TextInput(label="Convite Discord (opcional)", placeholder="https://discord.gg/exemplo", max_length=200, required=False)
    cor = discord.ui.TextInput(label="Cor (#RRGGBB)", placeholder="#9B59B6", max_length=7, required=False)

    def __init__(self, view):
        super().__init__()
        self.parent_view = view
        self.titulo.default = view.data.get("title", "")
        self.descricao.default = view.data.get("description", "")
        self.mensagem.default = view.data.get("message", "")
        self.convite.default = view.data.get("invite_url", "")
        self.cor.default = f"#{view.data.get('color', DEFAULT_COLOR):06X}"

    async def on_submit(self, interaction: discord.Interaction):
        try:
            color = parse_color(str(self.cor.value))
            invite = extract_invite(str(self.convite.value))
            if self.convite.value and not invite:
                raise ValueError("O link precisa ser um convite Discord válido.")

            self.parent_view.data.update({
                "title": str(self.titulo.value).strip(),
                "description": str(self.descricao.value).strip(),
                "message": str(self.mensagem.value).strip(),
                "invite_url": invite,
                "color": color,
            })

            await interaction.response.edit_message(
                embed=self.parent_view.cog.create_setup_embed(interaction.guild, self.parent_view.data),
                view=self.parent_view,
            )
        except ValueError as exc:
            await interaction.response.send_message(f"❌ {exc}", ephemeral=True)


class AutoMsgCreateView(discord.ui.View):
    def __init__(self, cog, user_id: int):
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = user_id
        self.data = {
            "channel_id": None,
            "interval_days": 5,
            "mode": "history",
            "title": "",
            "description": "",
            "message": "",
            "invite_url": "",
            "color": DEFAULT_COLOR,
        }
        self.add_item(AutoMsgCreateChannelSelect(self))
        self.add_item(AutoMsgModeSelect(self))
        self.add_item(AutoMsgIntervalSelect(self))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Este painel pertence a outra interação.", ephemeral=True)
            return False
        if not is_owner(interaction.user):
            await interaction.response.send_message("❌ Apenas o proprietário da Evelly pode usar este painel.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Conteúdo", emoji="📝", style=discord.ButtonStyle.primary, row=3)
    async def conteudo(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AutoMsgContentModal(self))

    @discord.ui.button(label="Criar agora", emoji="🚀", style=discord.ButtonStyle.success, row=3)
    async def criar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.data["channel_id"]:
            await interaction.response.send_message("❌ Escolha o canal primeiro.", ephemeral=True)
            return
        if not self.data["title"] and not self.data["description"] and not self.data["message"] and not self.data["invite_url"]:
            await interaction.response.send_message("❌ Configure pelo menos um conteúdo pelo botão **Conteúdo**.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        channel = guild.get_channel(self.data["channel_id"])
        if not isinstance(channel, discord.TextChannel):
            await interaction.followup.send("❌ Canal inválido.", ephemeral=True)
            return

        config = {
            "guild_id": guild.id,
            "channel_id": channel.id,
            "title": self.data["title"],
            "description": self.data["description"],
            "content": pack_content(self.data["message"], self.data["invite_url"]),
            "color": self.data["color"],
            "interval_days": self.data["interval_days"],
            "mode": self.data["mode"],
            "message_id": None,
        }

        message, ok, details = await self.cog.send_automation(guild, config, update_existing=False)
        if not ok:
            await interaction.followup.send(details, ephemeral=True)
            return

        next_send = now_utc() + timedelta(days=self.data["interval_days"])
        auto_id = criar_auto_message(
            guild_id=guild.id,
            channel_id=channel.id,
            title=self.data["title"],
            description=self.data["description"],
            content=config["content"],
            color=self.data["color"],
            interval_days=self.data["interval_days"],
            mode=self.data["mode"],
            message_id=message.id if message else None,
            next_send_at=iso(next_send),
            created_by=interaction.user.id,
        )

        if isinstance(auto_id, dict):
            auto_id = auto_id.get("id")

        if not auto_id:
            await interaction.followup.send(
                "⚠️ A mensagem foi enviada, mas não consegui salvar a automação no Supabase. "
                "Confira o console da Evelly.",
                ephemeral=True,
            )
            return

        auto_id = int(auto_id)

        registrar_auto_message_log(
            auto_message_id=auto_id,
            guild_id=guild.id,
            channel_id=channel.id,
            action="created",
            message_id=message.id if message else None,
            details=f"mode={self.data['mode']}; invite={self.data['invite_url'] or 'none'}",
        )

        await interaction.followup.send(
            f"✅ AutoMensagem `{auto_id}` criada e enviada agora.",
            ephemeral=True,
        )

    @discord.ui.button(label="Cancelar", emoji="✖️", style=discord.ButtonStyle.danger, row=3)
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Criação cancelada.", embed=None, view=None)


class AutoMsgCreateChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, parent):
        super().__init__(placeholder="📢 Escolha o canal", channel_types=[discord.ChannelType.text, discord.ChannelType.news], min_values=1, max_values=1, row=0)
        self.parent = parent

    async def callback(self, interaction: discord.Interaction):
        self.parent.data["channel_id"] = self.values[0].id
        await interaction.response.edit_message(embed=self.parent.cog.create_setup_embed(interaction.guild, self.parent.data), view=self.parent)


class AutoMsgModeSelect(discord.ui.Select):
    def __init__(self, parent):
        super().__init__(placeholder="🔄 Escolha o modo", options=[
            discord.SelectOption(label="Histórico", value="history", emoji="📚", description="Cria uma nova mensagem em cada ciclo."),
            discord.SelectOption(label="Atualizar", value="update", emoji="🔄", description="Edita a mesma mensagem em cada ciclo."),
        ], row=1)
        self.parent = parent

    async def callback(self, interaction: discord.Interaction):
        self.parent.data["mode"] = self.values[0]
        await interaction.response.edit_message(embed=self.parent.cog.create_setup_embed(interaction.guild, self.parent.data), view=self.parent)


class AutoMsgIntervalSelect(discord.ui.Select):
    def __init__(self, parent):
        super().__init__(placeholder="⏱️ Intervalo", options=[
            discord.SelectOption(label="1 dia", value="1"),
            discord.SelectOption(label="3 dias", value="3"),
            discord.SelectOption(label="5 dias", value="5"),
            discord.SelectOption(label="7 dias", value="7"),
            discord.SelectOption(label="15 dias", value="15"),
            discord.SelectOption(label="30 dias", value="30"),
        ], row=2)
        self.parent = parent

    async def callback(self, interaction: discord.Interaction):
        self.parent.data["interval_days"] = int(self.values[0])
        await interaction.response.edit_message(embed=self.parent.cog.create_setup_embed(interaction.guild, self.parent.data), view=self.parent)


class AutoMsgSelect(discord.ui.Select):
    def __init__(self, panel, items):
        self.panel = panel
        options = []
        for item in items[:25]:
            mode = "Atualizar" if item.get("mode") == "update" else "Histórico"
            status = "🟢" if item.get("enabled") else "🔴"
            options.append(discord.SelectOption(
                label=f"#{item.get('id')} • {mode}",
                value=str(item.get("id")),
                description=f"{status} • {item.get('interval_days', 0)} dia(s)",
            ))
        if not options:
            options = [discord.SelectOption(label="Nenhuma automação", value="0", description="Crie uma automação primeiro.")]
        super().__init__(placeholder="📨 Selecione uma AutoMensagem", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        value = int(self.values[0])

        if value == 0:
            await interaction.response.send_message(
                "📭 Nenhuma automação configurada.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        self.panel.selected_id = value

        item = pegar_auto_message(
            value,
            interaction.guild.id,
        )

        await interaction.edit_original_response(
            embed=self.panel.cog.panel_embed(
                interaction.guild,
                item,
            ),
            view=self.panel,
        )


class AutoMsgPanel(discord.ui.View):
    def __init__(self, cog, user_id: int, items):
        super().__init__(timeout=600)
        self.cog = cog
        self.user_id = user_id
        self.selected_id = None
        self.add_item(AutoMsgSelect(self, items))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Este painel pertence ao proprietário da Evelly.", ephemeral=True)
            return False
        if not is_owner(interaction.user):
            await interaction.response.send_message("❌ Apenas o proprietário da Evelly pode usar o AutoMensagem.", ephemeral=True)
            return False
        return True

    async def refresh(self, interaction):
        await interaction.response.defer()

        items = listar_auto_messages(interaction.guild.id)
        item = (
            pegar_auto_message(self.selected_id, interaction.guild.id)
            if self.selected_id
            else None
        )

        await interaction.edit_original_response(
            embed=self.cog.panel_embed(
                interaction.guild,
                item,
                len(items),
            ),
            view=AutoMsgPanel(
                self.cog,
                self.user_id,
                items,
            ),
        )

    @discord.ui.button(label="Criar", emoji="➕", style=discord.ButtonStyle.success, row=1)
    async def criar(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Acknowledge the Discord interaction immediately.
        # This prevents "Evelly did not respond in time" if Discord is
        # still processing the component/view update.
        await interaction.response.defer()
        view = AutoMsgCreateView(self.cog, self.user_id)
        await interaction.edit_original_response(
            embed=self.cog.create_setup_embed(interaction.guild, view.data),
            view=view,
        )

    @discord.ui.button(label="Ver detalhes", emoji="🔍", style=discord.ButtonStyle.primary, row=1)
    async def detalhes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_id:
            await interaction.response.send_message("❌ Selecione uma AutoMensagem primeiro.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        item = pegar_auto_message(
            self.selected_id,
            interaction.guild.id,
        )

        await interaction.followup.send(
            embed=self.cog.detail_embed(
                interaction.guild,
                item,
            ),
            ephemeral=True,
        )

    @discord.ui.button(label="Editar", emoji="✏️", style=discord.ButtonStyle.primary, row=1)
    async def editar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_id:
            await interaction.response.send_message("❌ Selecione uma AutoMensagem primeiro.", ephemeral=True)
            return

        # The edit view reads the configuration from Supabase. Since that
        # database call is synchronous, acknowledge the interaction first.
        await interaction.response.defer()

        view = AutoMsgEditView(
            self.cog,
            self.user_id,
            interaction.guild.id,
            self.selected_id,
        )

        await interaction.edit_original_response(
            embed=self.cog.create_setup_embed(interaction.guild, view.data),
            view=view,
        )

    @discord.ui.button(label="Ativar", emoji="🟢", style=discord.ButtonStyle.success, row=2)
    async def ativar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_id:
            await interaction.response.send_message("❌ Selecione uma AutoMensagem primeiro.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        item = pegar_auto_message(
            self.selected_id,
            interaction.guild.id,
        )

        atualizar_auto_message(
            self.selected_id,
            enabled=True,
        )

        registrar_auto_message_log(
            self.selected_id,
            interaction.guild.id,
            item.get("channel_id"),
            "enabled",
        )

        await interaction.followup.send(
            f"🟢 AutoMensagem `{self.selected_id}` ativada.",
            ephemeral=True,
        )

    @discord.ui.button(label="Desativar", emoji="🔴", style=discord.ButtonStyle.danger, row=2)
    async def desativar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_id:
            await interaction.response.send_message("❌ Selecione uma AutoMensagem primeiro.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        item = pegar_auto_message(
            self.selected_id,
            interaction.guild.id,
        )

        atualizar_auto_message(
            self.selected_id,
            enabled=False,
        )

        registrar_auto_message_log(
            self.selected_id,
            interaction.guild.id,
            item.get("channel_id"),
            "disabled",
        )

        await interaction.followup.send(
            f"🔴 AutoMensagem `{self.selected_id}` desativada.",
            ephemeral=True,
        )

    @discord.ui.button(label="Excluir", emoji="🗑️", style=discord.ButtonStyle.danger, row=2)
    async def excluir(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_id:
            await interaction.response.send_message("❌ Selecione uma AutoMensagem primeiro.", ephemeral=True)
            return

        await interaction.response.defer()

        item = pegar_auto_message(
            self.selected_id,
            interaction.guild.id,
        )

        if not excluir_auto_message(
            self.selected_id,
            interaction.guild.id,
        ):
            await interaction.edit_original_response(
                content="❌ Não foi possível excluir.",
            )
            return

        registrar_auto_message_log(
            self.selected_id,
            interaction.guild.id,
            item.get("channel_id"),
            "deleted",
        )

        self.selected_id = None

        items = listar_auto_messages(interaction.guild.id)

        await interaction.edit_original_response(
            content=None,
            embed=self.cog.panel_embed(
                interaction.guild,
                None,
                len(items),
            ),
            view=AutoMsgPanel(
                self.cog,
                self.user_id,
                items,
            ),
        )

    @discord.ui.button(label="Atualizar painel", emoji="🔄", style=discord.ButtonStyle.secondary, row=3)
    async def atualizar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.refresh(interaction)


class AutoMsgEditView(discord.ui.View):
    def __init__(self, cog, user_id: int, guild_id: int, auto_id: int):
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = user_id
        self.guild_id = guild_id
        self.auto_id = auto_id
        item = pegar_auto_message(auto_id, guild_id) or {}
        message, invite = unpack_content(item.get("content"))
        self.data = {
            "channel_id": item.get("channel_id"),
            "interval_days": int(item.get("interval_days") or 1),
            "mode": item.get("mode") or "history",
            "title": item.get("title") or "",
            "description": item.get("description") or "",
            "message": message,
            "invite_url": invite,
            "color": int(item.get("color") or DEFAULT_COLOR),
        }
        self.add_item(AutoMsgEditChannelSelect(self))
        self.add_item(AutoMsgEditModeSelect(self))
        self.add_item(AutoMsgEditIntervalSelect(self))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id or not is_owner(interaction.user):
            await interaction.response.send_message("❌ Apenas o proprietário da Evelly pode usar este painel.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Conteúdo", emoji="📝", style=discord.ButtonStyle.primary, row=3)
    async def conteudo(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AutoMsgContentModal(self))

    @discord.ui.button(label="Salvar alterações", emoji="💾", style=discord.ButtonStyle.success, row=3)
    async def salvar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.data["channel_id"]:
            await interaction.response.send_message("❌ Escolha um canal.", ephemeral=True)
            return

        if not self.data["title"] and not self.data["description"] and not self.data["message"] and not self.data["invite_url"]:
            await interaction.response.send_message("❌ Configure algum conteúdo.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        invite = extract_invite(self.data["invite_url"])
        dados = {
            "channel_id": self.data["channel_id"],
            "interval_days": self.data["interval_days"],
            "mode": self.data["mode"],
            "title": self.data["title"],
            "description": self.data["description"],
            "content": pack_content(self.data["message"], invite),
            "color": self.data["color"],
        }

        if not atualizar_auto_message(self.auto_id, **dados):
            await interaction.followup.send(
                "❌ Não foi possível salvar as alterações no Supabase.\n"
                "Confira o console da Evelly.",
                ephemeral=True,
            )
            return

        item = pegar_auto_message(self.auto_id, self.guild_id)
        if not item:
            await interaction.followup.send("⚠️ A configuração foi salva, mas não consegui recarregá-la.", ephemeral=True)
            return

        ok, details = await self.cog.aplicar_edicao_imediata(interaction.guild, item)

        registrar_auto_message_log(
            self.auto_id,
            self.guild_id,
            item.get("channel_id"),
            "edited" if ok else "edit_error",
            item.get("message_id"),
            details,
        )

        if ok:
            await interaction.followup.send(
                f"✅ AutoMensagem `{self.auto_id}` atualizada no Supabase e no Discord.",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                "⚠️ A configuração foi salva no Supabase, mas a mensagem não pôde ser atualizada.\n\n"
                f"{details}",
                ephemeral=True,
            )

    @discord.ui.button(label="Cancelar", emoji="✖️", style=discord.ButtonStyle.danger, row=3)
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Edição cancelada.", embed=None, view=None)


class AutoMsgEditChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, parent):
        super().__init__(placeholder="📢 Novo canal", channel_types=[discord.ChannelType.text, discord.ChannelType.news], min_values=1, max_values=1, row=0)
        self.parent = parent

    async def callback(self, interaction: discord.Interaction):
        self.parent.data["channel_id"] = self.values[0].id
        await interaction.response.edit_message(embed=self.parent.cog.create_setup_embed(interaction.guild, self.parent.data), view=self.parent)


class AutoMsgEditModeSelect(discord.ui.Select):
    def __init__(self, parent):
        super().__init__(placeholder="🔄 Novo modo", options=[
            discord.SelectOption(label="Histórico", value="history", emoji="📚"),
            discord.SelectOption(label="Atualizar", value="update", emoji="🔄"),
        ], row=1)
        self.parent = parent

    async def callback(self, interaction: discord.Interaction):
        self.parent.data["mode"] = self.values[0]
        await interaction.response.edit_message(embed=self.parent.cog.create_setup_embed(interaction.guild, self.parent.data), view=self.parent)


class AutoMsgEditIntervalSelect(discord.ui.Select):
    def __init__(self, parent):
        super().__init__(placeholder="⏱️ Novo intervalo", options=[
            discord.SelectOption(label="1 dia", value="1"),
            discord.SelectOption(label="3 dias", value="3"),
            discord.SelectOption(label="5 dias", value="5"),
            discord.SelectOption(label="7 dias", value="7"),
            discord.SelectOption(label="15 dias", value="15"),
            discord.SelectOption(label="30 dias", value="30"),
        ], row=2)
        self.parent = parent

    async def callback(self, interaction: discord.Interaction):
        self.parent.data["interval_days"] = int(self.values[0])
        await interaction.response.edit_message(embed=self.parent.cog.create_setup_embed(interaction.guild, self.parent.data), view=self.parent)


class AutoMsgEditModal(discord.ui.Modal, title="Editar AutoMensagem"):
    titulo = discord.ui.TextInput(label="Título", max_length=256, required=False)
    descricao = discord.ui.TextInput(label="Descrição", style=discord.TextStyle.paragraph, max_length=4000, required=False)
    mensagem = discord.ui.TextInput(label="Mensagem", style=discord.TextStyle.paragraph, max_length=2000, required=False)
    convite = discord.ui.TextInput(label="Convite Discord", max_length=200, required=False)
    cor = discord.ui.TextInput(label="Cor (#RRGGBB)", max_length=7, required=False)

    def __init__(self, cog, auto_id: int, guild_id: int):
        super().__init__()
        self.cog = cog
        self.auto_id = auto_id
        self.guild_id = guild_id
        item = pegar_auto_message(auto_id, guild_id) or {}
        message, invite = unpack_content(item.get("content"))
        self.titulo.default = item.get("title", "")
        self.descricao.default = item.get("description", "")
        self.mensagem.default = message
        self.convite.default = invite
        self.cor.default = f"#{item.get('color', DEFAULT_COLOR):06X}"

    async def on_submit(self, interaction: discord.Interaction):
        try:
            invite = extract_invite(str(self.convite.value))
            if self.convite.value and not invite:
                raise ValueError("O convite precisa ser um link Discord válido.")

            color = parse_color(str(self.cor.value))
            dados = {
                "title": str(self.titulo.value).strip(),
                "description": str(self.descricao.value).strip(),
                "content": pack_content(str(self.mensagem.value).strip(), invite),
                "color": color,
            }

            await interaction.response.defer(ephemeral=True)

            if not atualizar_auto_message(self.auto_id, **dados):
                await interaction.followup.send("❌ Não foi possível salvar a edição no Supabase.", ephemeral=True)
                return

            item = pegar_auto_message(self.auto_id, self.guild_id)
            if not item:
                await interaction.followup.send("⚠️ Salvei a edição, mas não consegui recarregar a automação.", ephemeral=True)
                return

            ok, details = await self.cog.aplicar_edicao_imediata(interaction.guild, item)

            registrar_auto_message_log(
                self.auto_id,
                self.guild_id,
                item.get("channel_id"),
                "edited" if ok else "edit_error",
                item.get("message_id"),
                details,
            )

            if ok:
                await interaction.followup.send(
                    f"✅ AutoMensagem `{self.auto_id}` atualizada no Discord.",
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    "⚠️ Salvei no banco, mas não consegui atualizar a mensagem no Discord.\n\n"
                    f"{details}",
                    ephemeral=True,
                )

        except ValueError as exc:
            if interaction.response.is_done():
                await interaction.followup.send(f"❌ {exc}", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ {exc}", ephemeral=True)


class AutoMensagem(commands.Cog):
    automsg = app_commands.Group(name="automsg", description="Painel de mensagens automáticas da Evelly.")

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.processar_automsg.start()
        print("📨 Sistema AutoMensagem carregado.", flush=True)

    def cog_unload(self):
        self.processar_automsg.cancel()

    def panel_embed(self, guild, selected=None, total=None):
        if selected:
            status = "🟢 Ativa" if selected.get("enabled") else "🔴 Desativada"
            mode = "🔄 Atualizar" if selected.get("mode") == "update" else "📚 Histórico"
            channel = guild.get_channel(int(selected.get("channel_id"))) if selected.get("channel_id") else None
            invite_message, invite_url = unpack_content(selected.get("content"))
            description = (
                f"**ID:** `{selected.get('id')}`\n"
                f"**Status:** {status}\n"
                f"**Canal:** {channel.mention if channel else 'Não encontrado'}\n"
                f"**Modo:** {mode}\n"
                f"**Intervalo:** `{selected.get('interval_days')} dia(s)`\n"
                f"**Convite:** {invite_url or 'Nenhum'}\n\n"
                "Use o seletor acima para trocar de automação."
            )
        else:
            description = "Nenhuma AutoMensagem selecionada. Use **Criar** para começar."
            if total is not None:
                description += f"\n\n📨 Automações cadastradas: `{total}`"
        embed = discord.Embed(title="📨 EVELLY • AUTOMENSAGEM", description=description, color=DEFAULT_COLOR)
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.set_footer(text="Evelly • AutoMensagem")
        return embed

    def create_setup_embed(self, guild, data):
        channel = guild.get_channel(data.get("channel_id")) if data.get("channel_id") else None
        mode = "🔄 Atualizar" if data.get("mode") == "update" else "📚 Histórico"
        desc = (
            f"📢 **Canal:** {channel.mention if channel else 'Não configurado'}\n"
            f"🔄 **Modo:** {mode}\n"
            f"⏱️ **Intervalo:** `{data.get('interval_days')} dia(s)`\n"
            f"🔗 **Convite:** {data.get('invite_url') or 'Nenhum'}\n"
            f"🎨 **Cor:** `#{data.get('color', DEFAULT_COLOR):06X}`\n\n"
            f"📝 **Título:** {data.get('title') or 'Nenhum'}\n"
            f"📄 **Descrição:** {truncate(data.get('description') or 'Nenhuma', 500)}\n"
            f"💬 **Mensagem:** {truncate(data.get('message') or 'Nenhuma', 500)}"
        )
        return discord.Embed(title="➕ Criar AutoMensagem", description=desc, color=data.get("color", DEFAULT_COLOR))

    def detail_embed(self, guild, item):
        if not item:
            return discord.Embed(title="❌ Automação não encontrada", color=0xE74C3C)
        msg, invite = unpack_content(item.get("content"))
        channel = guild.get_channel(int(item.get("channel_id"))) if item.get("channel_id") else None
        embed = discord.Embed(title=f"📨 AutoMensagem #{item.get('id')}", color=item.get("color", DEFAULT_COLOR))
        embed.add_field(name="Status", value="🟢 Ativa" if item.get("enabled") else "🔴 Desativada", inline=True)
        embed.add_field(name="Modo", value="🔄 Atualizar" if item.get("mode") == "update" else "📚 Histórico", inline=True)
        embed.add_field(name="Intervalo", value=f"{item.get('interval_days')} dia(s)", inline=True)
        embed.add_field(name="Canal", value=channel.mention if channel else str(item.get("channel_id")), inline=False)
        embed.add_field(name="Título", value=truncate(item.get("title") or "Nenhum", 1024), inline=False)
        embed.add_field(name="Descrição", value=truncate(item.get("description") or "Nenhuma", 1024), inline=False)
        embed.add_field(name="Mensagem", value=truncate(msg or "Nenhuma", 1024), inline=False)
        embed.add_field(name="Convite", value=invite or "Nenhum", inline=False)
        return embed

    async def aplicar_edicao_imediata(self, guild, item):
        """Aplica no Discord as alterações recém-salvas."""
        if not guild or not item:
            return False, "Servidor ou automação não encontrados."

        auto_id = int(item["id"])
        channel_id = item.get("channel_id")
        message_id = item.get("message_id")

        if not channel_id:
            return False, "A automação não possui canal configurado."

        channel = guild.get_channel(int(channel_id))
        if not isinstance(channel, discord.TextChannel):
            try:
                channel = await guild.fetch_channel(int(channel_id))
            except Exception as exc:
                return False, f"Não consegui acessar o canal: {exc}"

        if not message_id:
            message, ok, details = await self.send_automation(guild, item, update_existing=False)
            if not ok:
                return False, details
            atualizar_auto_message(auto_id, message_id=message.id)
            return True, "Mensagem criada e vinculada à automação."

        try:
            old = await channel.fetch_message(int(message_id))
        except discord.NotFound:
            message, ok, details = await self.send_automation(guild, item, update_existing=False)
            if not ok:
                return False, details
            atualizar_auto_message(auto_id, message_id=message.id)
            return True, "A mensagem antiga não existia mais; uma nova foi criada."
        except discord.Forbidden:
            return False, "A Evelly não tem permissão para acessar a mensagem antiga."
        except discord.HTTPException as exc:
            return False, f"Erro ao buscar a mensagem antiga: {exc}"

        # Se o canal foi trocado, o ID antigo pertence a outro canal.
        if old.channel.id != channel.id:
            message, ok, details = await self.send_automation(guild, item, update_existing=False)
            if not ok:
                return False, details
            atualizar_auto_message(auto_id, message_id=message.id)
            return True, "Canal alterado; nova mensagem criada no novo canal."

        message, ok, details = await self.send_automation(guild, item, update_existing=True)
        if not ok:
            return False, details

        atualizar_auto_message(auto_id, message_id=message.id, last_sent_at=iso(now_utc()))
        return True, "Mensagem editada imediatamente."

    async def send_automation(self, guild, config, update_existing=False):
        channel = guild.get_channel(int(config.get("channel_id")))
        if not isinstance(channel, discord.TextChannel):
            return None, False, "❌ Canal da automação não encontrado."

        raw_message, invite_url = unpack_content(config.get("content"))
        content = replace_vars(raw_message, guild, channel)
        title = replace_vars(config.get("title") or "", guild, channel)
        description = replace_vars(config.get("description") or "", guild, channel)
        color = int(config.get("color", DEFAULT_COLOR))

        embed = None
        button_view = None

        if invite_url:
            invite_embed, normalized, error = await make_invite_embed(self.bot, invite_url, description, color)
            if error:
                return None, False, error
            embed = invite_embed
            if title:
                embed.title = title
            button_view = discord.ui.View(timeout=None)
            button_view.add_item(discord.ui.Button(label="🚀 Ir para o Servidor", style=discord.ButtonStyle.link, url=normalized))
        else:
            embed = make_standard_embed(guild, channel, title, description, color)

        if not content and embed is None:
            return None, False, "❌ A automação não possui conteúdo."

        message_id = config.get("message_id")

        if update_existing and config.get("mode") == "update" and message_id:
            try:
                old = await channel.fetch_message(int(message_id))
                await old.edit(content=content or None, embed=embed, view=button_view)
                return old, True, "Mensagem atualizada."
            except discord.NotFound:
                pass
            except discord.Forbidden:
                return None, False, "❌ A Evelly não pode editar a mensagem nesse canal."
            except discord.HTTPException as exc:
                return None, False, f"❌ Erro ao editar a mensagem: {exc}"

        try:
            message = await channel.send(
                content=content or None,
                embed=embed,
                view=button_view,
                allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False),
            )
            return message, True, "Mensagem enviada."
        except discord.Forbidden:
            return None, False, "❌ A Evelly não tem permissão para enviar mensagens nesse canal."
        except discord.HTTPException as exc:
            return None, False, f"❌ Erro ao enviar mensagem: {exc}"

    @automsg.command(name="painel", description="Abre o painel visual do AutoMensagem.")
    async def painel(self, interaction: discord.Interaction):
        if not is_owner(interaction.user):
            await interaction.response.send_message("❌ Apenas o proprietário da Evelly pode usar o AutoMensagem.", ephemeral=True)
            return
        if not interaction.guild:
            await interaction.response.send_message("❌ Use este comando em um servidor.", ephemeral=True)
            return
        items = listar_auto_messages(interaction.guild.id)
        await interaction.response.send_message(embed=self.panel_embed(interaction.guild, None, len(items)), view=AutoMsgPanel(self, interaction.user.id, items), ephemeral=True)

    @automsg.command(name="limpar_painel", description="Fecha o painel do AutoMensagem.")
    async def limpar_painel(self, interaction: discord.Interaction):
        if not is_owner(interaction.user):
            await interaction.response.send_message("❌ Apenas o proprietário da Evelly pode usar o AutoMensagem.", ephemeral=True)
            return
        await interaction.response.send_message("🧹 Painel fechado.", ephemeral=True)

    @tasks.loop(seconds=PROCESS_INTERVAL_SECONDS)
    async def processar_automsg(self):
        try:
            registros = pegar_auto_messages_pendentes()
            for item in registros:
                try:
                    await self.processar_item(item)
                except Exception as exc:
                    print(f"[AUTOMSG] Erro no item {item.get('id')}: {exc}", flush=True)
        except Exception as exc:
            print(f"[AUTOMSG] Erro no processador: {exc}", flush=True)

    @processar_automsg.before_loop
    async def antes_processar(self):
        await self.bot.wait_until_ready()

    async def processar_item(self, item):
        auto_id = item.get("id")
        guild = self.bot.get_guild(int(item.get("guild_id")))
        if not guild or not item.get("enabled"):
            return
        next_send = parse_dt(item.get("next_send_at")) or now_utc()
        if next_send > now_utc():
            return

        interval = max(1, int(item.get("interval_days") or 1))
        new_next = now_utc() + timedelta(days=interval)

        # Atualiza o próximo ciclo antes do envio para reduzir duplicação em caso de concorrência.
        atualizar_auto_message(auto_id, next_send_at=iso(new_next))

        update_mode = item.get("mode") == "update"
        message, ok, details = await self.send_automation(guild, item, update_existing=update_mode)

        if not ok:
            atualizar_auto_message(auto_id, next_send_at=iso(now_utc() + timedelta(minutes=5)))
            registrar_auto_message_log(auto_id, guild.id, item.get("channel_id"), "error", item.get("message_id"), details)
            return

        atualizar_auto_message(
            auto_id,
            last_sent_at=iso(now_utc()),
            next_send_at=iso(new_next),
            message_id=message.id if message else item.get("message_id"),
        )

        registrar_auto_message_log(
            auto_id,
            guild.id,
            item.get("channel_id"),
            "updated" if update_mode else "sent",
            message.id if message else item.get("message_id"),
            details,
        )

    @automsg.command(name="listar", description="Lista as AutoMensagens cadastradas.")
    async def listar(self, interaction: discord.Interaction):
        if not is_owner(interaction.user):
            await interaction.response.send_message("❌ Apenas o proprietário da Evelly pode usar o AutoMensagem.", ephemeral=True)
            return
        items = listar_auto_messages(interaction.guild.id)
        if not items:
            await interaction.response.send_message("📭 Nenhuma AutoMensagem configurada.", ephemeral=True)
            return
        lines = []
        for item in items:
            mode = "Atualizar" if item.get("mode") == "update" else "Histórico"
            status = "🟢" if item.get("enabled") else "🔴"
            lines.append(f"{status} **#{item.get('id')}** • {mode} • {item.get('interval_days')}d")
        embed = discord.Embed(title="📨 AutoMensagens", description="\n".join(lines), color=DEFAULT_COLOR)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoMensagem(bot))
    print("📨 cogs.automsg carregado com sucesso", flush=True)
