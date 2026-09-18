import os
import re
from copy import deepcopy
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from supabase import create_client
from cogs.permissoes import pode_controlar_evelly

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_PUBLISHABLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "SUPABASE_URL e uma chave do Supabase precisam estar configuradas no .env."
    )

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

DEFAULT_CONFIG = {
    "ativo": False,
    "canal_id": None,
    "titulo": "💜 Seja muito bem-vindo(a) ao servidor!",
    "descricao": (
        "Olá, {mention}! 👋\n\n"
        "Você acabou de entrar no **{server}**.\n\n"
        "📜 Leia as regras em {regras}\n"
        "💬 Converse com a comunidade em {chat}\n"
        "🏷️ Confira seus cargos em {cargos}\n\n"
        "Esperamos que você se divirta por aqui! ✨"
    ),
    "conteudo": "{mention}",
    "cor": 0x9B59B6,
    "imagem_url": "",
    "gif_url": "",
    "thumbnail_servidor": True,
    "footer": "Evelly • Sistema de Boas-vindas",
    "canal_regras_id": None,
    "canal_chat_id": None,
    "canal_cargos_id": None,
    "cargo_id": None,
    "cargos_automaticos_ids": [],
    "dm_ativo": True,
    "dm_titulo": "💜 Bem-vindo(a) ao servidor!",
    "dm_descricao": (
        "Olá, {mention}! 👋\n\n"
        "Você acabou de entrar no **{server}**.\n\n"
        "Esperamos que você se divirta por aqui! ✨"
    ),
    "dm_conteudo": "",
}


def normalizar_config(config: Optional[dict]) -> dict:
    resultado = deepcopy(DEFAULT_CONFIG)
    if isinstance(config, dict):
        resultado.update(config)

    # Compatibilidade com configurações antigas que tinham apenas um cargo.
    cargos = resultado.get("cargos_automaticos_ids")
    if not isinstance(cargos, list):
        cargos = []
    cargos = [int(role_id) for role_id in cargos if str(role_id).isdigit()]

    # Não transforma automaticamente o antigo cargo_id em cargo automático.
    # cargo_id continua sendo o cargo exibido na mensagem; a lista nova controla
    # exclusivamente os cargos que serão atribuídos ao entrar.
    resultado["cargos_automaticos_ids"] = cargos[:10]
    resultado["dm_ativo"] = bool(resultado.get("dm_ativo", True))
    return resultado


def parse_cor(valor: str) -> int:
    valor = (valor or "").strip().replace("#", "")
    if not valor:
        return DEFAULT_CONFIG["cor"]
    if not re.fullmatch(r"[0-9a-fA-F]{6}", valor):
        raise ValueError("A cor precisa estar no formato #RRGGBB.")
    return int(valor, 16)


def url_valida(url: str) -> bool:
    if not url:
        return True
    return bool(re.match(r"^https?://\S+$", url.strip(), re.I))


def substituir_variaveis(texto: str, member: discord.Member, config: dict) -> str:
    if not texto:
        return ""

    guild = member.guild

    def mention_channel(channel_id):
        return f"<#${channel_id}>".replace("$", "") if channel_id else "#não-configurado"

    def mention_role(role_id):
        return f"<@&{role_id}>" if role_id else "@não-configurado"

    def mention_roles(role_ids):
        if not role_ids:
            return "@não-configurado"
        mentions = [mention_role(role_id) for role_id in role_ids if role_id]
        return " ".join(mentions) if mentions else "@não-configurado"

    valores = {
        "{user}": member.name,
        "{username}": member.name,
        "{mention}": member.mention,
        "{server}": guild.name,
        "{member_count}": str(guild.member_count or len(guild.members)),
        "{regras}": mention_channel(config.get("canal_regras_id")),
        "{chat}": mention_channel(config.get("canal_chat_id")),
        "{cargos}": mention_channel(config.get("canal_cargos_id")),
        "{cargo}": mention_role(config.get("cargo_id")),
        "{cargos_automaticos}": mention_roles(config.get("cargos_automaticos_ids", [])),
        "{id}": str(member.id),
    }

    for chave, valor in valores.items():
        texto = texto.replace(chave, valor)
    return texto


async def obter_config(guild_id: int) -> dict:
    resposta = (
        supabase.table("welcome_config")
        .select("config")
        .eq("guild_id", guild_id)
        .limit(1)
        .execute()
    )

    if not resposta.data:
        return normalizar_config(None)

    return normalizar_config(resposta.data[0].get("config"))


async def salvar_config(guild_id: int, config: dict) -> None:
    config = normalizar_config(config)
    (
        supabase.table("welcome_config")
        .upsert(
            {
                "guild_id": guild_id,
                "config": config,
            },
            on_conflict="guild_id",
        )
        .execute()
    )


def montar_embed(member: discord.Member, config: dict) -> discord.Embed:
    titulo = substituir_variaveis(config["titulo"], member, config)
    descricao = substituir_variaveis(config["descricao"], member, config)
    footer = substituir_variaveis(config["footer"], member, config)

    embed = discord.Embed(
        title=titulo,
        description=descricao,
        color=discord.Color(config.get("cor", DEFAULT_CONFIG["cor"])),
        timestamp=discord.utils.utcnow(),
    )

    if config.get("thumbnail_servidor", True) and member.guild.icon:
        embed.set_thumbnail(url=member.guild.icon.url)

    # GIF tem prioridade sobre imagem.
    midia = config.get("gif_url") or config.get("imagem_url")
    if midia:
        embed.set_image(url=midia)

    if footer:
        embed.set_footer(text=footer)

    return embed


def montar_embed_dm(member: discord.Member, config: dict) -> discord.Embed:
    titulo = substituir_variaveis(config.get("dm_titulo", DEFAULT_CONFIG["dm_titulo"]), member, config)
    descricao = substituir_variaveis(config.get("dm_descricao", DEFAULT_CONFIG["dm_descricao"]), member, config)
    embed = discord.Embed(
        title=titulo,
        description=descricao,
        color=discord.Color(config.get("cor", DEFAULT_CONFIG["cor"])),
        timestamp=discord.utils.utcnow(),
    )

    if member.guild.icon:
        embed.set_thumbnail(url=member.guild.icon.url)

    midia = config.get("gif_url") or config.get("imagem_url")
    if midia:
        embed.set_image(url=midia)

    footer = substituir_variaveis(config.get("footer", ""), member, config)
    if footer:
        embed.set_footer(text=footer)
    return embed


async def enviar_boas_vindas(
    member: discord.Member,
    config: dict,
    canal: discord.TextChannel | discord.Thread,
):
    embed = montar_embed(member, config)
    conteudo = substituir_variaveis(config.get("conteudo", ""), member, config)

    await canal.send(
        content=conteudo or None,
        embed=embed,
        allowed_mentions=discord.AllowedMentions(
            users=True,
            roles=True,
            everyone=False,
        ),
    )


async def enviar_boas_vindas_dm(member: discord.Member, config: dict) -> bool:
    if not config.get("dm_ativo", True):
        return False

    embed = montar_embed_dm(member, config)
    conteudo = substituir_variaveis(config.get("dm_conteudo", ""), member, config)

    try:
        await member.send(
            content=conteudo or None,
            embed=embed,
            allowed_mentions=discord.AllowedMentions(
                users=True,
                roles=False,
                everyone=False,
            ),
        )
        return True
    except discord.Forbidden:
        print(f"[WELCOME] DM bloqueada por {member} ({member.id})", flush=True)
        return False
    except discord.HTTPException as exc:
        print(f"[WELCOME] Erro HTTP enviando DM para {member}: {exc}", flush=True)
        return False


class WelcomeMessageModal(discord.ui.Modal, title="Mensagem de boas-vindas"):
    titulo = discord.ui.TextInput(
        label="Título",
        placeholder="💜 Seja muito bem-vindo(a)!",
        max_length=256,
        required=True,
    )

    descricao = discord.ui.TextInput(
        label="Descrição",
        style=discord.TextStyle.paragraph,
        placeholder="Use {mention}, {server}, {regras}, {chat}...",
        max_length=4000,
        required=True,
    )

    conteudo = discord.ui.TextInput(
        label="Mensagem acima do embed",
        placeholder="{mention}",
        max_length=1000,
        required=False,
    )

    cor = discord.ui.TextInput(
        label="Cor (#RRGGBB)",
        placeholder="#9B59B6",
        max_length=7,
        required=True,
    )

    footer = discord.ui.TextInput(
        label="Rodapé",
        placeholder="Evelly • Sistema de Boas-vindas",
        max_length=2048,
        required=False,
    )

    def __init__(self, cog, config: dict):
        super().__init__()
        self.cog = cog
        self.config = config

        self.titulo.default = config.get("titulo", "")
        self.descricao.default = config.get("descricao", "")
        self.conteudo.default = config.get("conteudo", "")
        self.cor.default = f"#{config.get('cor', DEFAULT_CONFIG['cor']):06X}"
        self.footer.default = config.get("footer", "")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            self.config["titulo"] = str(self.titulo.value).strip()
            self.config["descricao"] = str(self.descricao.value).strip()
            self.config["conteudo"] = str(self.conteudo.value).strip()
            self.config["cor"] = parse_cor(str(self.cor.value))
            self.config["footer"] = str(self.footer.value).strip()

            await salvar_config(interaction.guild.id, self.config)
            await interaction.response.send_message(
                "💜 **Mensagem atualizada e salva!**",
                ephemeral=True,
            )
        except ValueError as exc:
            await interaction.response.send_message(f"❌ {exc}", ephemeral=True)
        except Exception as exc:
            print(f"[WELCOME] Erro ao salvar mensagem: {exc}", flush=True)
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Não foi possível salvar a configuração.",
                    ephemeral=True,
                )


class WelcomeMediaModal(discord.ui.Modal, title="Imagem / GIF"):
    imagem = discord.ui.TextInput(
        label="URL da imagem",
        placeholder="https://...",
        max_length=1000,
        required=False,
    )

    gif = discord.ui.TextInput(
        label="URL do GIF",
        placeholder="https://...gif",
        max_length=1000,
        required=False,
    )

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.imagem.default = config.get("imagem_url", "")
        self.gif.default = config.get("gif_url", "")

    async def on_submit(self, interaction: discord.Interaction):
        imagem = str(self.imagem.value).strip()
        gif = str(self.gif.value).strip()

        if not url_valida(imagem) or not url_valida(gif):
            await interaction.response.send_message(
                "❌ Use URLs válidas começando com `http://` ou `https://`.",
                ephemeral=True,
            )
            return

        self.config["imagem_url"] = imagem
        self.config["gif_url"] = gif

        try:
            await salvar_config(interaction.guild.id, self.config)
            await interaction.response.send_message(
                "🖼️ **Mídia atualizada e salva!**\n"
                "Se os dois campos estiverem preenchidos, o GIF terá prioridade.",
                ephemeral=True,
            )
        except Exception as exc:
            print(f"[WELCOME] Erro ao salvar mídia: {exc}", flush=True)
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Não foi possível salvar a mídia.",
                    ephemeral=True,
                )


class WelcomeDMModal(discord.ui.Modal, title="Mensagem de boas-vindas na DM"):
    titulo = discord.ui.TextInput(
        label="Título da DM",
        placeholder="💜 Bem-vindo(a)!",
        max_length=256,
        required=True,
    )

    descricao = discord.ui.TextInput(
        label="Descrição da DM",
        style=discord.TextStyle.paragraph,
        placeholder="Use {mention}, {server}, {cargos_automaticos}...",
        max_length=4000,
        required=True,
    )

    conteudo = discord.ui.TextInput(
        label="Mensagem acima do embed",
        placeholder="Opcional",
        max_length=1000,
        required=False,
    )

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.titulo.default = config.get("dm_titulo", DEFAULT_CONFIG["dm_titulo"])
        self.descricao.default = config.get("dm_descricao", DEFAULT_CONFIG["dm_descricao"])
        self.conteudo.default = config.get("dm_conteudo", "")

    async def on_submit(self, interaction: discord.Interaction):
        self.config["dm_titulo"] = str(self.titulo.value).strip()
        self.config["dm_descricao"] = str(self.descricao.value).strip()
        self.config["dm_conteudo"] = str(self.conteudo.value).strip()

        try:
            await salvar_config(interaction.guild.id, self.config)
            await interaction.response.send_message(
                "💌 **Mensagem de DM atualizada e salva!**",
                ephemeral=True,
            )
        except Exception as exc:
            print(f"[WELCOME] Erro ao salvar DM: {exc}", flush=True)
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Não foi possível salvar a configuração da DM.",
                    ephemeral=True,
                )


class WelcomeChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, cog):
        super().__init__(
            placeholder="📢 Escolha o canal das boas-vindas",
            channel_types=[discord.ChannelType.text, discord.ChannelType.news],
            min_values=1,
            max_values=1,
            row=0,
        )
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        try:
            canal = self.values[0]
            config = await obter_config(interaction.guild.id)
            config["canal_id"] = canal.id
            await salvar_config(interaction.guild.id, config)
            await interaction.response.send_message(
                f"📢 Canal de boas-vindas definido como {canal.mention}.",
                ephemeral=True,
            )
        except Exception as exc:
            print(f"[WELCOME] Erro ao definir canal: {exc}", flush=True)
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Não foi possível salvar o canal.",
                    ephemeral=True,
                )


class WelcomeRulesSelect(discord.ui.ChannelSelect):
    def __init__(self, cog):
        super().__init__(
            placeholder="📚 Escolha os canais: regras, chat e cargos",
            channel_types=[discord.ChannelType.text, discord.ChannelType.news],
            min_values=0,
            max_values=3,
            row=1,
        )
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        try:
            config = await obter_config(interaction.guild.id)
            ids = [channel.id for channel in self.values]

            config["canal_regras_id"] = ids[0] if len(ids) > 0 else None
            config["canal_chat_id"] = ids[1] if len(ids) > 1 else None
            config["canal_cargos_id"] = ids[2] if len(ids) > 2 else None

            await salvar_config(interaction.guild.id, config)
            await interaction.response.send_message(
                "📚 Canais salvos na ordem: **1º Regras • 2º Chat • 3º Cargos**.",
                ephemeral=True,
            )
        except Exception as exc:
            print(f"[WELCOME] Erro ao salvar canais: {exc}", flush=True)
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Não foi possível salvar os canais.",
                    ephemeral=True,
                )


class WelcomeRoleSelect(discord.ui.RoleSelect):
    def __init__(self, cog):
        super().__init__(
            placeholder="🏷️ Escolha até 10 cargos automáticos",
            min_values=0,
            max_values=10,
            row=2,
        )
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        try:
            roles = [role for role in self.values if not role.is_default()]
            config = await obter_config(interaction.guild.id)
            config["cargos_automaticos_ids"] = [role.id for role in roles][:10]

            # Mantém o primeiro cargo também disponível na variável {cargo}.
            config["cargo_id"] = roles[0].id if roles else None
            await salvar_config(interaction.guild.id, config)

            if roles:
                lista = " ".join(role.mention for role in roles)
                msg = f"🏷️ Cargos automáticos salvos: {lista}"
            else:
                msg = "🏷️ Cargos automáticos removidos."

            await interaction.response.send_message(msg, ephemeral=True)
        except Exception as exc:
            print(f"[WELCOME] Erro ao salvar cargos automáticos: {exc}", flush=True)
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Não foi possível salvar os cargos automáticos.",
                    ephemeral=True,
                )


class WelcomePanel(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=300)
        self.cog = cog
        self.add_item(WelcomeChannelSelect(cog))
        self.add_item(WelcomeRulesSelect(cog))
        self.add_item(WelcomeRoleSelect(cog))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if pode_controlar_evelly(interaction.user):
            return True

        await interaction.response.send_message(
            "❌ Você não possui permissão para controlar a Evelly.",
            ephemeral=True,
        )
        return False

    @discord.ui.button(label="Editar mensagem", emoji="📝", style=discord.ButtonStyle.primary, row=3)
    async def editar(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = await obter_config(interaction.guild.id)
        await interaction.response.send_modal(WelcomeMessageModal(self.cog, config))

    @discord.ui.button(label="Imagem / GIF", emoji="🖼️", style=discord.ButtonStyle.secondary, row=3)
    async def midia(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = await obter_config(interaction.guild.id)
        await interaction.response.send_modal(WelcomeMediaModal(config))

    @discord.ui.button(label="Configurar DM", emoji="💌", style=discord.ButtonStyle.secondary, row=3)
    async def configurar_dm(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = await obter_config(interaction.guild.id)
        await interaction.response.send_modal(WelcomeDMModal(config))

    @discord.ui.button(label="Ativar", emoji="🟢", style=discord.ButtonStyle.success, row=4)
    async def ativar(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = await obter_config(interaction.guild.id)
        if not config.get("canal_id"):
            await interaction.response.send_message(
                "❌ Primeiro escolha o canal das boas-vindas.",
                ephemeral=True,
            )
            return
        config["ativo"] = True
        await salvar_config(interaction.guild.id, config)
        await interaction.response.send_message(
            "🟢 **Welcome ativado!** A Evelly enviará a mensagem no canal, atribuirá os cargos automáticos e tentará enviar a DM.",
            ephemeral=True,
        )

    @discord.ui.button(label="Desativar", emoji="🔴", style=discord.ButtonStyle.danger, row=4)
    async def desativar(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = await obter_config(interaction.guild.id)
        config["ativo"] = False
        await salvar_config(interaction.guild.id, config)
        await interaction.response.send_message("🔴 **Welcome desativado.**", ephemeral=True)

    @discord.ui.button(label="DM: ON/OFF", emoji="💌", style=discord.ButtonStyle.secondary, row=4)
    async def dm_toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = await obter_config(interaction.guild.id)
        config["dm_ativo"] = not config.get("dm_ativo", True)
        await salvar_config(interaction.guild.id, config)
        status = "ATIVADA 🟢" if config["dm_ativo"] else "DESATIVADA 🔴"
        await interaction.response.send_message(
            f"💌 DM de boas-vindas **{status}**.",
            ephemeral=True,
        )

    @discord.ui.button(label="Testar agora", emoji="👁️", style=discord.ButtonStyle.primary, row=4)
    async def testar(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = await obter_config(interaction.guild.id)
        member = interaction.guild.me or interaction.user
        embed = montar_embed(member, config)
        conteudo = substituir_variaveis(config.get("conteudo", ""), member, config)
        await interaction.response.send_message(
            content=conteudo or None,
            embed=embed,
            allowed_mentions=discord.AllowedMentions(users=True, roles=True),
            ephemeral=True,
        )

    @discord.ui.button(label="Atualizar painel", emoji="🔄", style=discord.ButtonStyle.secondary, row=4)
    async def atualizar(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = await obter_config(interaction.guild.id)
        embed = self.cog.painel_embed(interaction.guild, config)
        await interaction.response.edit_message(embed=embed, view=WelcomePanel(self.cog))


class Welcome(commands.Cog):
    """Sistema completo de boas-vindas da Evelly."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        print("💜 Sistema de boas-vindas: módulo carregado", flush=True)

    def painel_embed(self, guild: discord.Guild, config: dict) -> discord.Embed:
        canal = guild.get_channel(config.get("canal_id")) if config.get("canal_id") else None
        regras = guild.get_channel(config.get("canal_regras_id")) if config.get("canal_regras_id") else None
        chat = guild.get_channel(config.get("canal_chat_id")) if config.get("canal_chat_id") else None
        cargos = guild.get_channel(config.get("canal_cargos_id")) if config.get("canal_cargos_id") else None
        role = guild.get_role(config.get("cargo_id")) if config.get("cargo_id") else None
        auto_roles = [guild.get_role(role_id) for role_id in config.get("cargos_automaticos_ids", [])]
        auto_roles = [role for role in auto_roles if role is not None]
        auto_roles_text = " ".join(role.mention for role in auto_roles) if auto_roles else "Nenhum"

        embed = discord.Embed(
            title="💜 EVELLY • WELCOME SYSTEM",
            description=(
                "Configure o sistema de boas-vindas do seu servidor usando os controles abaixo.\n\n"
                f"🟢 **Status:** {'ATIVO' if config.get('ativo') else 'DESATIVADO'}\n"
                f"📢 **Canal:** {canal.mention if canal else 'Não configurado'}\n"
                f"📚 **Regras:** {regras.mention if regras else 'Não configurado'}\n"
                f"💬 **Chat:** {chat.mention if chat else 'Não configurado'}\n"
                f"🏷️ **Cargos:** {cargos.mention if cargos else 'Não configurado'}\n"
                f"🎖️ **Cargo:** {role.mention if role else 'Não configurado'}\n"
                f"🏷️ **Cargos automáticos:** {auto_roles_text}\n"
                f"💌 **DM:** {'ATIVA' if config.get('dm_ativo', True) else 'DESATIVADA'}\n"
                f"🎨 **Cor:** `#{config.get('cor', DEFAULT_CONFIG['cor']):06X}`\n"
                f"🖼️ **Mídia:** {'GIF' if config.get('gif_url') else 'Imagem' if config.get('imagem_url') else 'Nenhuma'}"
            ),
            color=discord.Color(config.get("cor", DEFAULT_CONFIG["cor"])),
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        midia = config.get("gif_url") or config.get("imagem_url")
        if midia:
            embed.set_image(url=midia)

        embed.set_footer(text="Evelly • Welcome System")
        return embed

    @app_commands.command(
        name="welcome",
        description="Abre o painel completo de boas-vindas da Evelly.",
    )
    @app_commands.check(lambda interaction: pode_controlar_evelly(interaction.user))
    async def welcome(self, interaction: discord.Interaction):
        """
        IMPORTANTE:
        O comando responde diretamente com response.send_message().
        Não usamos defer() aqui porque o projeto possui tratamento global
        de AppCommandError e o erro anterior era 40060 (interação já reconhecida).
        """
        interaction_id = interaction.id
        print(
            f"[WELCOME] /welcome recebido | interaction_id={interaction_id} | "
            f"response_done={interaction.response.is_done()}",
            flush=True,
        )

        try:
            if interaction.guild is None:
                await interaction.response.send_message(
                    "❌ Este comando só pode ser usado dentro de um servidor.",
                    ephemeral=True,
                )
                return

            config = await obter_config(interaction.guild.id)
            embed = self.painel_embed(interaction.guild, config)

            # PRIMEIRA E ÚNICA resposta da interação do comando.
            await interaction.response.send_message(
                embed=embed,
                view=WelcomePanel(self),
                ephemeral=True,
            )

            print(
                f"[WELCOME] /welcome respondido com sucesso | interaction_id={interaction_id}",
                flush=True,
            )

        except discord.NotFound:
            print(
                f"[WELCOME] Interação expirada/desconhecida | interaction_id={interaction_id}",
                flush=True,
            )
        except discord.HTTPException as exc:
            print(
                f"[WELCOME] HTTPException | interaction_id={interaction_id} | "
                f"status={exc.status} | code={getattr(exc, 'code', None)} | {exc}",
                flush=True,
            )
            # Não tenta responder novamente aqui.
            # O retry de response.send_message() seria justamente capaz de gerar 40060.
        except Exception as exc:
            print(
                f"[WELCOME] Erro ao abrir painel | interaction_id={interaction_id} | "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )
            # Não fazemos uma segunda resposta da interação.

    @app_commands.command(
        name="welcome_teste",
        description="Testa a mensagem de boas-vindas.",
    )
    @app_commands.check(lambda interaction: pode_controlar_evelly(interaction.user))
    async def welcome_teste(self, interaction: discord.Interaction):
        config = await obter_config(interaction.guild.id)
        embed = montar_embed(interaction.user, config)
        conteudo = substituir_variaveis(config.get("conteudo", ""), interaction.user, config)
        await interaction.response.send_message(
            content=conteudo or None,
            embed=embed,
            allowed_mentions=discord.AllowedMentions(users=True, roles=True),
        )

    @app_commands.command(
        name="welcome_ativar",
        description="Ativa o sistema de boas-vindas.",
    )
    @app_commands.check(lambda interaction: pode_controlar_evelly(interaction.user))
    async def welcome_ativar(self, interaction: discord.Interaction):
        config = await obter_config(interaction.guild.id)
        if not config.get("canal_id"):
            await interaction.response.send_message(
                "❌ Configure o canal primeiro usando `/welcome`.",
                ephemeral=True,
            )
            return

        config["ativo"] = True
        await salvar_config(interaction.guild.id, config)
        await interaction.response.send_message(
            "🟢 Sistema de boas-vindas **ativado**!"
        )

    @app_commands.command(
        name="welcome_desativar",
        description="Desativa o sistema de boas-vindas.",
    )
    @app_commands.check(lambda interaction: pode_controlar_evelly(interaction.user))
    async def welcome_desativar(self, interaction: discord.Interaction):
        config = await obter_config(interaction.guild.id)
        config["ativo"] = False
        await salvar_config(interaction.guild.id, config)
        await interaction.response.send_message(
            "🔴 Sistema de boas-vindas **desativado**!"
        )

    @app_commands.command(
        name="welcome_midia",
        description="Define imagem e/ou GIF por anexo.",
    )
    @app_commands.check(lambda interaction: pode_controlar_evelly(interaction.user))
    @app_commands.describe(imagem="Imagem anexada", gif="GIF anexado")
    async def welcome_midia(
        self,
        interaction: discord.Interaction,
        imagem: Optional[discord.Attachment] = None,
        gif: Optional[discord.Attachment] = None,
    ):
        if not imagem and not gif:
            await interaction.response.send_message(
                "❌ Envie pelo menos uma imagem ou GIF.",
                ephemeral=True,
            )
            return

        config = await obter_config(interaction.guild.id)
        if imagem:
            config["imagem_url"] = imagem.url
        if gif:
            config["gif_url"] = gif.url

        await salvar_config(interaction.guild.id, config)
        await interaction.response.send_message(
            "🖼️ Mídia salva com sucesso! O GIF terá prioridade sobre a imagem.",
            ephemeral=True,
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        try:
            config = await obter_config(member.guild.id)

            if not config.get("ativo"):
                return

            # 1) Atribui os cargos automáticos configurados.
            cargos_config = config.get("cargos_automaticos_ids", [])
            roles = []
            for role_id in cargos_config:
                role = member.guild.get_role(role_id)
                if role is None or role.is_default() or role.managed:
                    continue
                roles.append(role)

            if roles:
                try:
                    await member.add_roles(
                        *roles,
                        reason="Evelly • cargo automático de entrada",
                    )
                    print(
                        f"[WELCOME] Cargos automáticos atribuídos para {member}: "
                        f"{', '.join(role.name for role in roles)}",
                        flush=True,
                    )
                except discord.Forbidden:
                    print(
                        f"[WELCOME] Sem permissão/hierarquia para atribuir cargos a {member}",
                        flush=True,
                    )
                except discord.HTTPException as exc:
                    print(
                        f"[WELCOME] Erro HTTP atribuindo cargos a {member}: {exc}",
                        flush=True,
                    )

            # 2) Mensagem pública, caso um canal tenha sido configurado.
            canal = member.guild.get_channel(config.get("canal_id")) if config.get("canal_id") else None
            if canal is not None and isinstance(canal, (discord.TextChannel, discord.Thread)):
                await enviar_boas_vindas(member, config, canal)
                print(
                    f"[WELCOME] Boas-vindas públicas enviadas para {member} em {member.guild.name}",
                    flush=True,
                )

            # 3) DM de boas-vindas. Falha de DM não impede o restante do sistema.
            if config.get("dm_ativo", True):
                enviada = await enviar_boas_vindas_dm(member, config)
                print(
                    f"[WELCOME] DM {'enviada' if enviada else 'não enviada'} para {member}",
                    flush=True,
                )

        except Exception as exc:
            print(f"[WELCOME] Erro no on_member_join: {exc}", flush=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))
    print("💜 cogs.welcome carregado com sucesso", flush=True)
