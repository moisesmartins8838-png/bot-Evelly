import asyncio
import io
import re
from html import escape as html_escape
import time
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

from database.database import supabase
from cogs.permissoes import pode_controlar_evelly

PURPLE = 0x8E44AD

TEMP_VOICE_MARKER = "EVELLY_TEMP_TICKET_CALL"
TEMP_VOICE_GRACE_SECONDS = 60


def parse_ticket_emoji(value):
    """
    Aceita:
    - emoji Unicode: 🎫
    - emoji personalizado estático: <:nome:id>
    - emoji personalizado animado: <a:nome:id>
    """
    if value is None:
        return "🎫"

    value = str(value).strip()

    if not value:
        return "🎫"

    if value.startswith("<") and value.endswith(">"):
        try:
            parsed = discord.PartialEmoji.from_str(value)
            if parsed.id:
                return parsed
        except Exception as e:
            print(
                f"[TICKET] Emoji personalizado inválido: {value} | {e}",
                flush=True,
            )

    return value



def is_staff(member: discord.Member, role_id: int | None) -> bool:
    if pode_controlar_evelly(member):
        return True
    if not role_id:
        return False
    return any(role.id == int(role_id) for role in member.roles)


def cfg_ticket(guild_id: int):
    try:
        r = (
            supabase.table("evelly_ticket_config")
            .select("*")
            .eq("guild_id", guild_id)
            .limit(1)
            .execute()
        )
        return r.data[0] if r.data else None
    except Exception as e:
        print(f"[TICKET] Config error: {e}", flush=True)
        return None


def save_ticket_cfg(guild_id, category_id, staff_role_id, panel_channel_id=None):
    try:
        supabase.table("evelly_ticket_config").upsert({
            "guild_id": int(guild_id),
            "category_id": int(category_id),
            "staff_role_id": int(staff_role_id),
            "panel_channel_id": int(panel_channel_id) if panel_channel_id else None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, on_conflict="guild_id").execute()
        return True
    except Exception as e:
        print(f"[TICKET] Save config error: {e}", flush=True)
        return False


def create_ticket_db(guild_id, channel_id, user_id, category):
    try:
        r = supabase.table("evelly_tickets").insert({
            "guild_id": int(guild_id),
            "channel_id": int(channel_id),
            "user_id": int(user_id),
            "category": category,
            "status": "open",
        }).execute()
        return r.data[0] if r.data else None
    except Exception as e:
        print(f"[TICKET] Create DB error: {e}", flush=True)
        return None


def find_open_ticket(guild_id, user_id):
    try:
        r = (
            supabase.table("evelly_tickets")
            .select("*")
            .eq("guild_id", guild_id)
            .eq("user_id", user_id)
            .eq("status", "open")
            .limit(1)
            .execute()
        )
        return r.data[0] if r.data else None
    except Exception as e:
        print(f"[TICKET] Find error: {e}", flush=True)
        return None


def get_ticket_by_channel(channel_id):
    try:
        r = (
            supabase.table("evelly_tickets")
            .select("*")
            .eq("channel_id", int(channel_id))
            .limit(1)
            .execute()
        )
        return r.data[0] if r.data else None
    except Exception as e:
        print(f"[TICKET] Lookup error: {e}", flush=True)
        return None


def get_categories(guild_id):
    try:
        r = (
            supabase.table("evelly_ticket_categories")
            .select("*")
            .eq("guild_id", int(guild_id))
            .eq("enabled", True)
            .order("position")
            .limit(25)
            .execute()
        )
        return r.data or []
    except Exception as e:
        print(f"[TICKET] Categories error: {e}", flush=True)
        return []


def seed_default_categories(guild_id):
    try:
        existing = get_categories(guild_id)
        if existing:
            return existing

        defaults = [
            ("duvidas", "Dúvidas", "Retire suas dúvidas.", "❓", 1),
            ("denuncias", "Denúncias", "Faça uma denúncia aqui.", "🚨", 2),
            ("bug", "Relatar Bug", "Relate bugs do nosso servidor.", "🛠️", 3),
            ("parcerias", "Parcerias", "Inicie ou finalize uma parceria conosco.", "🤝", 4),
            ("sugestoes", "Sugestões", "Compartilhe suas ideias conosco.", "💡", 5),
        ]

        payload = [{
            "guild_id": int(guild_id),
            "key": key,
            "label": label,
            "description": description,
            "emoji": str(emoji).strip(),
            "position": position,
            "enabled": True,
        } for key, label, description, emoji, position in defaults]

        supabase.table("evelly_ticket_categories").insert(payload).execute()
        return get_categories(guild_id)
    except Exception as e:
        print(f"[TICKET] Seed categories error: {e}", flush=True)
        return []


def create_category_db(guild_id, key, label, description, emoji, position):
    try:
        r = supabase.table("evelly_ticket_categories").insert({
            "guild_id": int(guild_id),
            "key": key,
            "label": label,
            "description": description,
            "emoji": emoji,
            "position": int(position),
            "enabled": True,
        }).execute()
        return r.data[0] if r.data else None
    except Exception as e:
        print(f"[TICKET] Create category error: {e}", flush=True)
        return None


def delete_category_db(guild_id, key):
    try:
        r = (
            supabase.table("evelly_ticket_categories")
            .delete()
            .eq("guild_id", int(guild_id))
            .eq("key", key)
            .execute()
        )
        return bool(r.data)
    except Exception as e:
        print(f"[TICKET] Delete category error: {e}", flush=True)
        return False


def close_ticket_db(channel_id, closed_by):
    try:
        r = (
            supabase.table("evelly_tickets")
            .update({
                "status": "closed",
                "closed_at": datetime.now(timezone.utc).isoformat(),
                "closed_by": int(closed_by),
            })
            .eq("channel_id", int(channel_id))
            .eq("status", "open")
            .execute()
        )
        return bool(r.data)
    except Exception as e:
        print(f"[TICKET] Close DB error: {e}", flush=True)
        return False


def clean_text(value):
    if value is None:
        return ""
    return str(value).replace("\r", "").replace("\x00", "")


async def generate_transcript(channel: discord.TextChannel, ticket: dict):
    # Gera um transcript HTML organizado e visual.
    generated_at = datetime.now(timezone.utc)
    messages_html = []
    message_count = 0

    async for message in channel.history(limit=None, oldest_first=True):
        message_count += 1
        created = message.created_at.astimezone(timezone.utc)
        created_text = created.strftime("%d/%m/%Y às %H:%M:%S UTC")

        author_name = html_escape(str(message.author))
        author_id = html_escape(str(message.author.id))

        try:
            avatar_url = html_escape(
                str(message.author.display_avatar.url),
                quote=True
            )
            author_avatar = f'<img class="avatar" src="{avatar_url}" alt="Avatar">'
        except Exception:
            author_avatar = '<div class="avatar fallback">E</div>'

        body_parts = []

        content = clean_text(message.content)
        if content:
            body_parts.append(
                f'<div class="message-content">{html_escape(content)}</div>'
            )

        if message.attachments:
            items = []
            for attachment in message.attachments:
                filename = html_escape(attachment.filename)
                url = html_escape(attachment.url, quote=True)
                items.append(
                    f'''
                    <a class="attachment" href="{url}" target="_blank" rel="noopener">
                        <span class="attachment-icon">📎</span>
                        <span>
                            <strong>{filename}</strong>
                            <small>Abrir anexo</small>
                        </span>
                    </a>
                    '''
                )

            body_parts.append(
                '<div class="attachments">' + "".join(items) + '</div>'
            )

        if message.embeds:
            embeds = []

            for embed in message.embeds:
                title = html_escape(embed.title or "Embed")
                description = html_escape(
                    clean_text(embed.description)
                    if embed.description
                    else ""
                )

                link = ""
                if embed.url:
                    safe_url = html_escape(embed.url, quote=True)
                    link = (
                        f'<a href="{safe_url}" target="_blank" '
                        f'rel="noopener">Abrir link ↗</a>'
                    )

                embeds.append(
                    f'''
                    <div class="discord-embed">
                        <div class="embed-title">▌ {title}</div>
                        {f'<div class="embed-description">{description}</div>' if description else ''}
                        {link}
                    </div>
                    '''
                )

            body_parts.append(
                '<div class="embeds">' + "".join(embeds) + '</div>'
            )

        if message.reference and message.reference.message_id:
            body_parts.insert(
                0,
                (
                    '<div class="reply-reference">'
                    f'↪ Resposta à mensagem '
                    f'<code>{message.reference.message_id}</code>'
                    '</div>'
                )
            )

        if not body_parts:
            body_parts.append(
                '<div class="message-content empty">Mensagem sem texto.</div>'
            )

        messages_html.append(
            f'''
            <article class="message">
                {author_avatar}
                <div class="message-main">
                    <div class="message-header">
                        <span class="author">{author_name}</span>
                        <span class="author-id">ID {author_id}</span>
                        <time>{created_text}</time>
                    </div>
                    <div class="message-body">
                        {''.join(body_parts)}
                    </div>
                </div>
            </article>
            '''
        )

    server_name = html_escape(channel.guild.name)
    server_id = html_escape(str(channel.guild.id))
    channel_name = html_escape(channel.name)
    channel_id = html_escape(str(channel.id))
    user_id = html_escape(str(ticket.get("user_id", "N/A")))
    category = html_escape(str(ticket.get("category", "atendimento")))
    ticket_id = html_escape(str(ticket.get("id", "N/A")))

    html_document = f'''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Evelly • Ticket #{ticket_id}</title>
<style>
* {{ box-sizing: border-box; }}
body {{
    margin: 0; padding: 32px 18px;
    background: #111318; color: #e8e9ed;
    font-family: Inter, Segoe UI, Arial, sans-serif;
    line-height: 1.55;
}}
.container {{ max-width: 980px; margin: 0 auto; }}
.header {{
    background: linear-gradient(135deg, #2b1640, #171922);
    border: 1px solid #4d286d; border-radius: 18px;
    padding: 28px; box-shadow: 0 12px 40px rgba(0,0,0,.28);
    margin-bottom: 18px;
}}
.brand {{ display:flex; align-items:center; gap:12px; margin-bottom:22px; }}
.brand-icon {{
    width:48px; height:48px; border-radius:14px;
    display:flex; align-items:center; justify-content:center;
    background:#8e44ad; font-size:25px;
}}
.brand-title {{ font-size:24px; font-weight:800; }}
.brand-subtitle {{ color:#aaaebb; font-size:13px; }}
.title {{ font-size:30px; font-weight:800; margin:0 0 6px; }}
.subtitle {{ color:#aeb2c0; margin:0; }}
.stats {{
    display:grid; grid-template-columns:repeat(4,1fr);
    gap:10px; margin-top:22px;
}}
.stat {{
    background:rgba(255,255,255,.045);
    border:1px solid rgba(255,255,255,.08);
    border-radius:12px; padding:13px;
}}
.stat-label {{
    display:block; color:#9297a6; font-size:11px;
    text-transform:uppercase; letter-spacing:.7px; margin-bottom:4px;
}}
.stat-value {{ font-weight:700; word-break:break-word; }}
.messages {{
    background:#191b21; border:1px solid #292c35;
    border-radius:18px; overflow:hidden;
}}
.messages-header {{
    padding:18px 22px; border-bottom:1px solid #292c35;
    font-weight:800; font-size:17px;
}}
.message {{
    display:flex; gap:13px; padding:18px 22px;
    border-bottom:1px solid #292c35;
}}
.message:last-child {{ border-bottom:0; }}
.avatar {{
    width:40px; height:40px; min-width:40px;
    border-radius:50%; object-fit:cover; background:#292c35;
}}
.fallback {{
    display:flex; align-items:center; justify-content:center;
    font-weight:800; color:white; background:#8e44ad;
}}
.message-main {{ min-width:0; flex:1; }}
.message-header {{
    display:flex; align-items:baseline; gap:8px;
    flex-wrap:wrap; margin-bottom:7px;
}}
.author {{ font-weight:800; color:#fff; }}
.author-id, time {{ color:#7f8492; font-size:11px; }}
.message-content {{
    white-space:pre-wrap; overflow-wrap:anywhere; color:#e5e7eb;
}}
.empty {{ color:#777d8b; font-style:italic; }}
.reply-reference {{
    display:inline-block; background:#22252d; color:#9298a8;
    border-left:3px solid #8e44ad; border-radius:5px;
    padding:5px 9px; font-size:11px; margin-bottom:8px;
}}
code {{ color:#c9a7db; }}
.attachments {{ display:flex; flex-direction:column; gap:7px; margin-top:10px; }}
.attachment {{
    display:flex; align-items:center; gap:10px;
    width:fit-content; max-width:100%; padding:9px 12px;
    background:#22252d; border:1px solid #343844;
    border-radius:9px; color:#e8e9ed; text-decoration:none;
}}
.attachment:hover {{ border-color:#8e44ad; }}
.attachment-icon {{ font-size:20px; }}
.attachment small {{ display:block; color:#858a98; }}
.discord-embed {{
    margin-top:10px; padding:12px 14px;
    border-left:4px solid #8e44ad;
    background:#20232a; border-radius:5px;
}}
.embed-title {{ font-weight:800; }}
.embed-description {{ margin-top:5px; white-space:pre-wrap; }}
.discord-embed a {{ display:inline-block; margin-top:8px; color:#b77bd4; }}
.footer {{ text-align:center; color:#747987; font-size:11px; padding:18px; }}
@media (max-width:700px) {{
    body {{ padding:12px; }}
    .stats {{ grid-template-columns:repeat(2,1fr); }}
    .header {{ padding:20px; }}
    .title {{ font-size:23px; }}
    .message {{ padding:15px; }}
}}
</style>
</head>
<body>
<div class="container">
<section class="header">
    <div class="brand">
        <div class="brand-icon">🎫</div>
        <div>
            <div class="brand-title">Evelly</div>
            <div class="brand-subtitle">Histórico de Atendimento</div>
        </div>
    </div>
    <h1 class="title">Ticket #{ticket_id}</h1>
    <p class="subtitle">Transcrição completa do atendimento encerrado.</p>
    <div class="stats">
        <div class="stat"><span class="stat-label">Servidor</span><span class="stat-value">{server_name}</span></div>
        <div class="stat"><span class="stat-label">Canal</span><span class="stat-value">#{channel_name}</span></div>
        <div class="stat"><span class="stat-label">Categoria</span><span class="stat-value">{category}</span></div>
        <div class="stat"><span class="stat-label">Mensagens</span><span class="stat-value">{message_count}</span></div>
    </div>
</section>
<section class="messages">
    <div class="messages-header">💬 Histórico da conversa</div>
    {''.join(messages_html)}
</section>
<div class="footer">
    Gerado pela Evelly • {generated_at.strftime("%d/%m/%Y às %H:%M:%S UTC")}<br>
    Servidor ID: {server_id} • Canal ID: {channel_id} • Usuário ID: {user_id}
</div>
</div>
</body>
</html>
'''

    return html_document.encode("utf-8")


async def send_transcript_dm(member: discord.Member, ticket: dict, transcript: bytes):
    filename = f"ticket-{ticket.get('id', 'sem-id')}-transcript.html"

    embed = discord.Embed(
        title="📄 Histórico do seu atendimento",
        description=(
            "Seu ticket foi encerrado com sucesso.\n\n"
            "O histórico completo da conversa está anexado abaixo "
            "em um formato organizado para visualização."
        ),
        color=PURPLE,
        timestamp=discord.utils.utcnow(),
    )

    embed.add_field(name="🎫 Ticket", value=f"`#{ticket.get('id', 'N/A')}`", inline=True)
    embed.add_field(name="📌 Categoria", value=f"`{str(ticket.get('category', 'atendimento'))}`", inline=True)
    embed.add_field(name="🏠 Servidor", value=f"`{member.guild.name}`", inline=True)
    embed.add_field(name="📎 Formato", value="`HTML • Transcript completo`", inline=True)
    embed.add_field(
        name="🔐 Privacidade",
        value="Este histórico foi enviado somente para você.",
        inline=False,
    )

    if member.guild.me:
        embed.set_author(
            name="Evelly • Sistema de Tickets",
            icon_url=member.guild.me.display_avatar.url,
        )

    embed.set_footer(text="Evelly • Histórico de Atendimento")

    await member.send(
        embed=embed,
        file=discord.File(
            io.BytesIO(transcript),
            filename=filename,
        ),
    )

class TicketCategorySelect(discord.ui.Select):
    def __init__(self, cog, categories):
        self.cog = cog

        options = []
        for category in categories[:25]:
            emoji = parse_ticket_emoji(category.get("emoji") or "🎫")
            options.append(
                discord.SelectOption(
                    label=str(category["label"])[:100],
                    value=str(category["key"])[:100],
                    description=str(category.get("description") or "Abrir atendimento.")[:100],
                    emoji=emoji,
                )
            )

        if not options:
            options = [
                discord.SelectOption(
                    label="Sem categorias",
                    value="none",
                    description="Nenhuma categoria de atendimento foi configurada.",
                    emoji="⚠️",
                )
            ]

        super().__init__(
            placeholder="Selecione uma opção...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="evelly_ticket_category",
        )

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message(
                "❌ Nenhuma categoria de atendimento está disponível.",
                ephemeral=True,
            )
            return

        await self.cog.criar_ticket(interaction, self.values[0])


class TicketPanelView(discord.ui.View):
    def __init__(self, cog, categories):
        super().__init__(timeout=None)
        self.cog = cog
        self.add_item(TicketCategorySelect(cog, categories))


class TicketActionsView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    def _cfg(self, interaction):
        return cfg_ticket(interaction.guild.id) if interaction.guild else None

    async def _is_staff(self, interaction):
        cfg = self._cfg(interaction)
        role_id = cfg.get("staff_role_id") if cfg else None
        return is_staff(interaction.user, role_id), cfg

    async def _get_ticket(self, interaction):
        return get_ticket_by_channel(interaction.channel.id)

    @discord.ui.button(
        label="Notificar",
        emoji="🔔",
        style=discord.ButtonStyle.secondary,
        custom_id="evelly_ticket_notify",
    )
    async def notify(self, interaction: discord.Interaction, button: discord.ui.Button):
        permitido, _ = await self._is_staff(interaction)
        if not permitido:
            await interaction.response.send_message(
                "❌ Apenas a equipe autorizada pode notificar o cliente.",
                ephemeral=True,
            )
            return

        ticket = await self._get_ticket(interaction)
        if not ticket:
            await interaction.response.send_message(
                "❌ Não consegui localizar este ticket.",
                ephemeral=True,
            )
            return

        member = interaction.guild.get_member(int(ticket["user_id"]))
        if not member:
            await interaction.response.send_message(
                "❌ O usuário não está mais neste servidor.",
                ephemeral=True,
            )
            return

        mensagem = (
            f"🔔 **A equipe chamou você!**\n"
            f"Seu atendimento no ticket **#{ticket.get('id')}** precisa da sua atenção."
        )

        dm_ok = True
        try:
            await member.send(
                embed=discord.Embed(
                    title="🔔 Notificação de atendimento",
                    description=mensagem,
                    color=PURPLE,
                )
            )
        except Exception as e:
            dm_ok = False
            print(f"[TICKET] DM notification error: {e}", flush=True)

        await interaction.channel.send(
            f"🔔 {member.mention}, a equipe solicitou sua atenção neste ticket.",
            allowed_mentions=discord.AllowedMentions(users=True),
        )

        if dm_ok:
            resposta = "✅ Cliente notificado no ticket e por mensagem privada."
        else:
            resposta = (
                "⚠️ Cliente notificado no ticket, mas não consegui enviar a DM "
                "(DM fechada ou bloqueada)."
            )

        await interaction.response.send_message(resposta, ephemeral=True)

    @discord.ui.button(
        label="Reivindicar Ticket",
        emoji="👤",
        style=discord.ButtonStyle.primary,
        custom_id="evelly_ticket_claim",
    )
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        permitido, _ = await self._is_staff(interaction)
        if not permitido:
            await interaction.response.send_message(
                "❌ Apenas a equipe autorizada pode reivindicar este ticket.",
                ephemeral=True,
            )
            return

        ticket = await self._get_ticket(interaction)
        if not ticket:
            await interaction.response.send_message(
                "❌ Não consegui localizar este ticket.",
                ephemeral=True,
            )
            return

        claimed_by = ticket.get("claimed_by")
        if claimed_by and int(claimed_by) != interaction.user.id:
            outro = interaction.guild.get_member(int(claimed_by))
            nome = outro.mention if outro else f"<@{claimed_by}>"
            await interaction.response.send_message(
                f"⚠️ Este ticket já foi reivindicado por {nome}.",
                ephemeral=True,
            )
            return

        try:
            supabase.table("evelly_tickets").update({
                "claimed_by": int(interaction.user.id),
                "claimed_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", int(ticket["id"])).execute()

            await interaction.channel.send(
                f"💜 {interaction.user.mention} **reivindicou o seu ticket e irá te atender!**",
                allowed_mentions=discord.AllowedMentions(users=True),
            )

            await interaction.response.send_message(
                "✅ Você reivindicou este ticket.",
                ephemeral=True,
            )
        except Exception as e:
            print(f"[TICKET] Claim error: {e}", flush=True)
            await interaction.response.send_message(
                "❌ Não consegui registrar a reivindicação.",
                ephemeral=True,
            )

    @discord.ui.button(
        label="Atendimento Concluído",
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id="evelly_ticket_complete",
    )
    async def complete(self, interaction: discord.Interaction, button: discord.ui.Button):
        permitido, _ = await self._is_staff(interaction)
        if not permitido:
            await interaction.response.send_message(
                "❌ Apenas a equipe autorizada pode concluir o atendimento.",
                ephemeral=True,
            )
            return

        ticket = await self._get_ticket(interaction)
        if not ticket:
            await interaction.response.send_message(
                "❌ Não consegui localizar este ticket.",
                ephemeral=True,
            )
            return

        try:
            result = (
                supabase.table("evelly_tickets")
                .update({
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                })
                .eq("id", int(ticket["id"]))
                .eq("status", "open")
                .execute()
            )

            if not result.data:
                await interaction.response.send_message(
                    "❌ Não consegui registrar a conclusão.",
                    ephemeral=True,
                )
                return

            await interaction.channel.send(
                f"✅ **Atendimento concluído por {interaction.user.mention}.**\n"
                "O ticket continuará aberto até ser fechado.",
                allowed_mentions=discord.AllowedMentions(users=True),
            )
            await interaction.response.send_message(
                "✅ Atendimento marcado como concluído.",
                ephemeral=True,
            )
        except Exception as e:
            print(f"[TICKET] Complete error: {e}", flush=True)
            await interaction.response.send_message(
                "❌ Ocorreu um erro ao concluir o atendimento.",
                ephemeral=True,
            )

    @discord.ui.button(
        label="Criar Call",
        emoji="🔊",
        style=discord.ButtonStyle.secondary,
        custom_id="evelly_ticket_create_call",
    )
    async def create_call(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        permitido, cfg = await self._is_staff(interaction)

        if not permitido:
            await interaction.response.send_message(
                "❌ Apenas o cargo da equipe configurado nos tickets "
                "pode criar uma call.",
                ephemeral=True,
            )
            return

        ticket = await self._get_ticket(interaction)

        if not ticket:
            await interaction.response.send_message(
                "❌ Não consegui localizar este ticket.",
                ephemeral=True,
            )
            return

        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "❌ Este botão só pode ser usado dentro de um servidor.",
                ephemeral=True,
            )
            return

        ticket_id = ticket.get("id", interaction.channel.id)

        # Evita criar várias calls para o mesmo ticket.
        existing_call = discord.utils.find(
            lambda channel: (
                isinstance(channel, discord.VoiceChannel)
                and channel.topic
                and f"{TEMP_VOICE_MARKER}:{ticket_id}" in channel.topic
            ),
            guild.channels,
        )

        if existing_call:
            await interaction.response.send_message(
                f"🔊 A call deste ticket já existe: {existing_call.mention}",
                ephemeral=True,
            )
            return

        category = None

        if cfg:
            category = guild.get_channel(int(cfg["category_id"]))

        if not isinstance(category, discord.CategoryChannel):
            category = interaction.channel.category

        staff_role = None

        if cfg and cfg.get("staff_role_id"):
            staff_role = guild.get_role(int(cfg["staff_role_id"]))

        if not staff_role:
            await interaction.response.send_message(
                "❌ O cargo da equipe configurado nos tickets não existe mais.",
                ephemeral=True,
            )
            return

        ticket_user = guild.get_member(int(ticket["user_id"]))

        if not ticket_user:
            await interaction.response.send_message(
                "❌ O usuário deste ticket não está mais no servidor.",
                ephemeral=True,
            )
            return

        bot_member = guild.me

        if bot_member is None:
            await interaction.response.send_message(
                "❌ Não consegui identificar a Evelly no servidor.",
                ephemeral=True,
            )
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False,
                connect=False,
            ),
            staff_role: discord.PermissionOverwrite(
                view_channel=True,
                connect=True,
                speak=True,
                stream=True,
                use_voice_activation=True,
            ),
            ticket_user: discord.PermissionOverwrite(
                view_channel=True,
                connect=True,
                speak=True,
                stream=True,
                use_voice_activation=True,
            ),
            bot_member: discord.PermissionOverwrite(
                view_channel=True,
                connect=True,
                speak=True,
                manage_channels=True,
            ),
        }

        await interaction.response.defer(ephemeral=True)

        try:
            voice_channel = await guild.create_voice_channel(
                name=f"🔊・atendimento-{ticket_id}",
                category=category,
                overwrites=overwrites,
                topic=f"{TEMP_VOICE_MARKER}:{ticket_id}:{int(time.time())}",
                reason=f"Evelly • Call temporária do ticket #{ticket_id}",
            )

            await interaction.followup.send(
                "🔊 **Call criada com sucesso!**\n\n"
                f"📞 Canal: {voice_channel.mention}\n"
                f"👤 Cliente: {ticket_user.mention}\n"
                "🗑️ Ela será apagada automaticamente quando ficar vazia.",
                ephemeral=True,
            )

            try:
                await interaction.channel.send(
                    f"🔊 {interaction.user.mention} criou uma call temporária: "
                    f"{voice_channel.mention}",
                    allowed_mentions=discord.AllowedMentions(users=True),
                )
            except Exception:
                pass

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Não tenho permissão para criar canais de voz.",
                ephemeral=True,
            )

        except discord.HTTPException as e:
            print(f"[TICKET] Create voice HTTP error: {e}", flush=True)
            await interaction.followup.send(
                "❌ O Discord recusou a criação da call.",
                ephemeral=True,
            )

        except Exception as e:
            print(f"[TICKET] Create voice error: {e}", flush=True)
            await interaction.followup.send(
                "❌ Ocorreu um erro ao criar a call.",
                ephemeral=True,
            )

    @discord.ui.button(
        label="Fechar Ticket",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        custom_id="evelly_ticket_close",
    )
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        permitido, _ = await self._is_staff(interaction)
        if not permitido:
            await interaction.response.send_message(
                "❌ Apenas a equipe autorizada pode fechar este ticket.",
                ephemeral=True,
            )
            return

        ticket = await self._get_ticket(interaction)
        if not ticket:
            await interaction.response.send_message(
                "❌ Não consegui localizar este ticket.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        try:
            transcript = await generate_transcript(interaction.channel, ticket)

            # Tenta enviar a cópia privada antes de apagar o canal.
            member = interaction.guild.get_member(int(ticket["user_id"]))
            dm_ok = False

            if member:
                try:
                    await send_transcript_dm(member, ticket, transcript)
                    dm_ok = True
                except Exception as e:
                    print(f"[TICKET] Transcript DM error: {e}", flush=True)

            close_ticket_db(interaction.channel.id, interaction.user.id)

            if dm_ok:
                await interaction.channel.send(
                    "📄 Log do atendimento gerada e enviada no privado do cliente.\n"
                    "🔒 Este ticket será fechado em 5 segundos."
                )
            else:
                await interaction.channel.send(
                    "📄 Log do atendimento gerada, mas não foi possível enviar "
                    "a cópia no privado do cliente.\n"
                    "🔒 Este ticket será fechado em 5 segundos."
                )

            await asyncio.sleep(5)

            try:
                await interaction.channel.delete(
                    reason=f"Ticket fechado por {interaction.user}"
                )
            except Exception as e:
                print(f"[TICKET] Delete error: {e}", flush=True)

        except Exception as e:
            print(f"[TICKET] Close error: {e}", flush=True)
            try:
                await interaction.followup.send(
                    "❌ Ocorreu um erro ao gerar o log/fechar o ticket.",
                    ephemeral=True,
                )
            except Exception:
                pass


class Ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cleanup_temp_voice_channels.start()

    ticket = app_commands.Group(
        name="ticket",
        description="Sistema de atendimento da Evelly.",
    )

    categoria = app_commands.Group(
        name="categoria",
        description="Gerencia as categorias de atendimento.",
    )

    @ticket.command(
        name="configurar",
        description="Configura categoria do Discord e cargo da equipe.",
    )
    @app_commands.describe(
        categoria="Categoria do Discord onde os tickets serão criados.",
        equipe="Cargo que terá acesso aos tickets.",
    )
    async def configurar(
        self,
        interaction: discord.Interaction,
        categoria: discord.CategoryChannel,
        equipe: discord.Role,
    ):
        if not pode_controlar_evelly(interaction.user):
            await interaction.response.send_message(
                "❌ Você não possui permissão para configurar tickets.",
                ephemeral=True,
            )
            return

        ok = save_ticket_cfg(
            interaction.guild.id,
            categoria.id,
            equipe.id,
        )
        if not ok:
            await interaction.response.send_message(
                "❌ Não consegui salvar a configuração.",
                ephemeral=True,
            )
            return

        seed_default_categories(interaction.guild.id)

        await interaction.response.send_message(
            "✅ **Tickets configurados!**\n\n"
            f"📁 Categoria do Discord: {categoria.mention}\n"
            f"🛡️ Equipe: {equipe.mention}\n\n"
            "Agora use `/ticket painel` para publicar o painel.",
            ephemeral=True,
        )

    @ticket.command(
        name="painel",
        description="Publica o painel de abertura de tickets.",
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

        cfg = cfg_ticket(interaction.guild.id)
        if not cfg:
            await interaction.response.send_message(
                "❌ Configure primeiro com `/ticket configurar`.",
                ephemeral=True,
            )
            return

        categories = seed_default_categories(interaction.guild.id)

        embed = discord.Embed(
            title="🎫 Atendimento — LN Store",
            description=(
                "Precisa de ajuda? Selecione abaixo o tipo de atendimento que você precisa.\n\n"
                "Um canal privado será criado automaticamente e nossa equipe poderá "
                "reivindicar o atendimento."
            ),
            color=PURPLE,
        )
        embed.add_field(
            name="📌 Como funciona?",
            value=(
                "1. Escolha uma categoria.\n"
                "2. A Evelly criará seu atendimento privado.\n"
                "3. Um atendente poderá reivindicar o ticket.\n"
                "4. Ao finalizar, o histórico será enviado para sua DM."
            ),
            inline=False,
        )
        embed.set_footer(text="Evelly • Sistema de Atendimento")

        await canal.send(
            embed=embed,
            view=TicketPanelView(self, categories),
        )

        save_ticket_cfg(
            interaction.guild.id,
            cfg["category_id"],
            cfg["staff_role_id"],
            canal.id,
        )

        await interaction.response.send_message(
            f"✅ Painel de tickets publicado em {canal.mention}.",
            ephemeral=True,
        )

    @categoria.command(
        name="criar",
        description="Cria uma nova categoria de atendimento.",
    )
    @app_commands.describe(
        nome="Nome exibido no painel.",
        emoji="Emoji da categoria.",
        descricao="Descrição exibida no menu.",
    )
    async def categoria_criar(
        self,
        interaction: discord.Interaction,
        nome: str,
        emoji: str,
        descricao: str,
    ):
        if not pode_controlar_evelly(interaction.user):
            await interaction.response.send_message(
                "❌ Você não possui permissão para gerenciar categorias.",
                ephemeral=True,
            )
            return

        nome_limpo = re.sub(r"[^a-z0-9]+", "-", nome.lower()).strip("-")[:40]
        if not nome_limpo:
            await interaction.response.send_message(
                "❌ Use um nome válido para a categoria.",
                ephemeral=True,
            )
            return

        categories = get_categories(interaction.guild.id)
        if len(categories) >= 25:
            await interaction.response.send_message(
                "❌ O Discord permite no máximo 25 opções neste menu.",
                ephemeral=True,
            )
            return

        position = len(categories) + 1
        created = create_category_db(
            interaction.guild.id,
            nome_limpo,
            nome[:100],
            descricao[:100],
            emoji[:10],
            position,
        )

        if not created:
            await interaction.response.send_message(
                "❌ Não consegui criar a categoria. Talvez essa chave já exista.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"✅ Categoria **{nome[:100]}** criada com {emoji}.\n"
            "Para aparecer no painel, publique um novo `/ticket painel`.",
            ephemeral=True,
        )

    @categoria.command(
        name="excluir",
        description="Exclui uma categoria do painel.",
    )
    @app_commands.describe(
        nome="Nome/chave da categoria que será excluída.",
    )
    async def categoria_excluir(
        self,
        interaction: discord.Interaction,
        nome: str,
    ):
        if not pode_controlar_evelly(interaction.user):
            await interaction.response.send_message(
                "❌ Você não possui permissão para gerenciar categorias.",
                ephemeral=True,
            )
            return

        key = re.sub(r"[^a-z0-9]+", "-", nome.lower()).strip("-")[:40]
        if not delete_category_db(interaction.guild.id, key):
            await interaction.response.send_message(
                "❌ Não encontrei essa categoria.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"🗑️ Categoria **{nome}** excluída.\n"
            "Publique novamente o painel para atualizar o menu.",
            ephemeral=True,
        )

    @categoria.command(
        name="listar",
        description="Lista as categorias de atendimento.",
    )
    async def categoria_listar(self, interaction: discord.Interaction):
        if not pode_controlar_evelly(interaction.user):
            await interaction.response.send_message(
                "❌ Você não possui permissão para ver as categorias.",
                ephemeral=True,
            )
            return

        categories = get_categories(interaction.guild.id)
        if not categories:
            await interaction.response.send_message(
                "📭 Nenhuma categoria configurada.",
                ephemeral=True,
            )
            return

        texto = "\n".join(
            f"{c.get('emoji', '🎫')} **{c['label']}** — `{c['key']}`"
            for c in categories
        )

        await interaction.response.send_message(
            f"### 🎫 Categorias de atendimento\n{texto}",
            ephemeral=True,
        )

    @categoria.command(
        name="atualizar",
        description="Altera emoji, nome ou descrição de uma categoria.",
    )
    @app_commands.describe(
        chave="Chave atual da categoria.",
        nome="Novo nome exibido.",
        emoji="Novo emoji.",
        descricao="Nova descrição.",
    )
    async def categoria_atualizar(
        self,
        interaction: discord.Interaction,
        chave: str,
        nome: str,
        emoji: str,
        descricao: str,
    ):
        if not pode_controlar_evelly(interaction.user):
            await interaction.response.send_message(
                "❌ Você não possui permissão para gerenciar categorias.",
                ephemeral=True,
            )
            return

        key = re.sub(r"[^a-z0-9]+", "-", chave.lower()).strip("-")[:40]

        try:
            result = (
                supabase.table("evelly_ticket_categories")
                .update({
                    "label": nome[:100],
                    "description": descricao[:100],
                    "emoji": str(emoji).strip(),
                })
                .eq("guild_id", interaction.guild.id)
                .eq("key", key)
                .execute()
            )

            if not result.data:
                await interaction.response.send_message(
                    "❌ Categoria não encontrada.",
                    ephemeral=True,
                )
                return

            await interaction.response.send_message(
                f"✅ Categoria **{nome[:100]}** atualizada.\n"
                "Publique novamente o painel para aplicar as alterações.",
                ephemeral=True,
            )
        except Exception as e:
            print(f"[TICKET] Update category error: {e}", flush=True)
            await interaction.response.send_message(
                "❌ Não consegui atualizar a categoria.",
                ephemeral=True,
            )

    @ticket.command(
        name="fechar",
        description="Fecha o ticket atual e gera o log.",
    )
    async def fechar(self, interaction: discord.Interaction):
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ Este comando precisa ser usado dentro de um ticket.",
                ephemeral=True,
            )
            return

        cfg = cfg_ticket(interaction.guild.id)
        if not cfg or not is_staff(
            interaction.user,
            cfg.get("staff_role_id"),
        ):
            await interaction.response.send_message(
                "❌ Você não possui permissão para fechar este ticket.",
                ephemeral=True,
            )
            return

        # Reutiliza a mesma lógica do botão.
        view = TicketActionsView(self)
        await interaction.response.send_message(
            "🔒 Fechando ticket e gerando o histórico...",
            ephemeral=True,
        )
        await view._close_ticket_from_command(interaction)

    async def criar_ticket(self, interaction: discord.Interaction, categoria_nome: str):
        guild = interaction.guild
        if not guild:
            return

        cfg = cfg_ticket(guild.id)
        if not cfg:
            await interaction.response.send_message(
                "❌ O sistema de tickets ainda não foi configurado.",
                ephemeral=True,
            )
            return

        existente = find_open_ticket(guild.id, interaction.user.id)
        if existente:
            canal_existente = guild.get_channel(int(existente["channel_id"]))
            if canal_existente:
                await interaction.response.send_message(
                    f"⚠️ Você já possui um ticket aberto: {canal_existente.mention}",
                    ephemeral=True,
                )
                return

        categoria_cfg = None
        for category in get_categories(guild.id):
            if category["key"] == categoria_nome:
                categoria_cfg = category
                break

        if not categoria_cfg:
            await interaction.response.send_message(
                "❌ Essa categoria não está mais disponível. Publique o painel novamente.",
                ephemeral=True,
            )
            return

        categoria = guild.get_channel(int(cfg["category_id"]))
        staff_role = guild.get_role(int(cfg["staff_role_id"]))

        if not isinstance(categoria, discord.CategoryChannel) or not staff_role:
            await interaction.response.send_message(
                "❌ A categoria do Discord ou o cargo da equipe não existe mais.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                read_message_history=True,
                manage_messages=True,
            ),
            staff_role: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True,
            ),
        }

        nome_usuario = re.sub(
            r"[^a-z0-9-]",
            "-",
            interaction.user.name.lower(),
        ).strip("-")[:45] or "usuario"

        slug = re.sub(
            r"[^a-z0-9-]",
            "-",
            categoria_cfg["key"].lower(),
        ).strip("-")[:25]

        canal = await guild.create_text_channel(
            name=f"{slug}-{nome_usuario}",
            category=categoria,
            overwrites=overwrites,
            topic=(
                f"Ticket de {interaction.user} • ID {interaction.user.id} "
                f"• Tipo {categoria_cfg['key']}"
            ),
            reason="Evelly • criação de ticket",
        )

        registro = create_ticket_db(
            guild.id,
            canal.id,
            interaction.user.id,
            categoria_cfg["key"],
        )

        if not registro:
            await canal.delete(reason="Falha ao registrar ticket")
            await interaction.followup.send(
                "❌ Não consegui registrar o ticket no Supabase.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=f"{categoria_cfg.get('emoji', '🎫')} {categoria_cfg['label']} — LN Store",
            description=(
                f"Olá, {interaction.user.mention}!\n\n"
                "Seu atendimento foi criado com sucesso.\n"
                "Aguarde um atendente reivindicar seu ticket."
            ),
            color=PURPLE,
        )
        embed.add_field(
            name="👤 Cliente",
            value=interaction.user.mention,
            inline=True,
        )
        embed.add_field(
            name="📌 Status",
            value="🟡 Aguardando atendimento",
            inline=True,
        )
        embed.add_field(
            name="🗂️ Categoria",
            value=f"{categoria_cfg.get('emoji', '🎫')} {categoria_cfg['label']}",
            inline=True,
        )
        embed.set_footer(
            text="Evelly • Atendimento • Utilize os botões abaixo."
        )

        await canal.send(
            content=f"{interaction.user.mention} {staff_role.mention}",
            embed=embed,
            view=TicketActionsView(self),
            allowed_mentions=discord.AllowedMentions(
                users=True,
                roles=True,
            ),
        )

        await interaction.followup.send(
            f"✅ Seu atendimento foi criado: {canal.mention}",
            ephemeral=True,
        )

    async def cog_load(self):
        # O painel é recriado dinamicamente por servidor, portanto não
        # registramos um menu global com categorias antigas.
        self.bot.add_view(TicketActionsView(self))

    def cog_unload(self):
        if self.cleanup_temp_voice_channels.is_running():
            self.cleanup_temp_voice_channels.cancel()

    @tasks.loop(seconds=30)
    async def cleanup_temp_voice_channels(self):
        """
        Remove calls temporárias que estejam vazias.
        Existe uma tolerância de 60 segundos após a criação para
        evitar que uma call recém-criada seja apagada antes do uso.
        """
        agora = int(time.time())

        for guild in self.bot.guilds:
            for channel in list(guild.voice_channels):
                topic = channel.topic or ""

                if not topic.startswith(TEMP_VOICE_MARKER + ":"):
                    continue

                try:
                    partes = topic.split(":")
                    criado_em = int(partes[-1])
                except (ValueError, IndexError):
                    criado_em = agora

                if channel.members:
                    continue

                if agora - criado_em < TEMP_VOICE_GRACE_SECONDS:
                    continue

                try:
                    await channel.delete(
                        reason="Evelly • Call temporária vazia"
                    )
                    print(
                        f"[TICKET] Call temporária removida: "
                        f"{guild.name} / {channel.name}",
                        flush=True,
                    )
                except discord.NotFound:
                    pass
                except discord.Forbidden:
                    print(
                        f"[TICKET] Sem permissão para remover call: "
                        f"{guild.name} / {channel.name}",
                        flush=True,
                    )
                except discord.HTTPException as e:
                    print(
                        f"[TICKET] Erro removendo call temporária: {e}",
                        flush=True,
                    )

    @cleanup_temp_voice_channels.before_loop
    async def before_cleanup_temp_voice_channels(self):
        await self.bot.wait_until_ready()


# Método auxiliar para fechar via comando, compartilhando a mesma rotina do botão.
async def _close_ticket_from_command(self, interaction):
    ticket = get_ticket_by_channel(interaction.channel.id)
    if not ticket:
        return

    try:
        transcript = await generate_transcript(interaction.channel, ticket)
        member = interaction.guild.get_member(int(ticket["user_id"]))
        dm_ok = False

        if member:
            try:
                await send_transcript_dm(member, ticket, transcript)
                dm_ok = True
            except Exception as e:
                print(f"[TICKET] Transcript DM error: {e}", flush=True)

        close_ticket_db(interaction.channel.id, interaction.user.id)

        await interaction.channel.send(
            "📄 Log gerada e enviada no privado do cliente."
            if dm_ok else
            "📄 Log gerada, mas não foi possível enviar a cópia no privado do cliente."
        )
        await asyncio.sleep(5)
        await interaction.channel.delete(
            reason=f"Ticket fechado por {interaction.user}"
        )
    except Exception as e:
        print(f"[TICKET] Command close error: {e}", flush=True)

TicketActionsView._close_ticket_from_command = _close_ticket_from_command


async def setup(bot):
    await bot.add_cog(Ticket(bot))
    print("🎫 cogs.ticket carregado com sucesso", flush=True)
