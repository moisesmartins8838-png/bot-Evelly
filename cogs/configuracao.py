import discord

from discord import app_commands
from discord.ext import commands

from database.database import (
    criar_servidor,
    pegar_servidor,
    configurar_canal_notificacao,
    remover_canal_notificacao,
    configurar_cargo_notificacao,
    remover_cargo_notificacao,
    configurar_mensagem_youtube,
    remover_mensagem_youtube
)


class Configuracao(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # =====================================================
    # /CONFIG
    # =====================================================

    @app_commands.command(
        name="config",
        description="Mostra as configurações da Evelly."
    )
    async def config(
        self,
        interaction: discord.Interaction
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                "❌ Este comando só pode ser usado em um servidor.",
                ephemeral=True
            )

            return

        guild_id = interaction.guild.id

        criar_servidor(guild_id)

        servidor = pegar_servidor(guild_id)

        if not servidor:

            await interaction.response.send_message(
                "❌ Não consegui carregar as configurações.",
                ephemeral=True
            )

            return

        canal_id = servidor[1]
        cargo_id = servidor[2]
        mensagem = servidor[3]
        youtube = servidor[4]
        boas_vindas = servidor[5]

        # -------------------------------------------------
        # CANAL
        # -------------------------------------------------

        if canal_id:

            canal = interaction.guild.get_channel(
                canal_id
            )

            if canal:

                canal_texto = canal.mention

            else:

                canal_texto = (
                    f"⚠️ Canal não encontrado\n"
                    f"`{canal_id}`"
                )

        else:

            canal_texto = "❌ Não configurado"

        # -------------------------------------------------
        # CARGO
        # -------------------------------------------------

        if cargo_id:

            cargo = interaction.guild.get_role(
                cargo_id
            )

            if cargo:

                cargo_texto = cargo.mention

            else:

                cargo_texto = (
                    f"⚠️ Cargo não encontrado\n"
                    f"`{cargo_id}`"
                )

        else:

            cargo_texto = "❌ Não configurado"

        # -------------------------------------------------
        # YOUTUBE
        # -------------------------------------------------

        youtube_texto = (
            "🟢 Ativado"
            if youtube
            else
            "🔴 Desativado"
        )

        # -------------------------------------------------
        # BOAS VINDAS
        # -------------------------------------------------

        boas_vindas_texto = (
            "🟢 Ativado"
            if boas_vindas
            else
            "🔴 Desativado"
        )

        # -------------------------------------------------
        # MENSAGEM
        # -------------------------------------------------

        mensagem_texto = (
            mensagem
            if mensagem
            else
            "Padrão da Evelly"
        )

        if len(mensagem_texto) > 1000:

            mensagem_texto = (
                mensagem_texto[:997]
                + "..."
            )

        # -------------------------------------------------
        # EMBED
        # -------------------------------------------------

        embed = discord.Embed(
            title="⚙️ Configuração da Evelly",
            description=(
                "Aqui estão as configurações atuais "
                "deste servidor."
            ),
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="🎬 YouTube",
            value=youtube_texto,
            inline=True
        )

        embed.add_field(
            name="👋 Boas-vindas",
            value=boas_vindas_texto,
            inline=True
        )

        embed.add_field(
            name="📢 Canal de notificações",
            value=canal_texto,
            inline=False
        )

        embed.add_field(
            name="🔔 Cargo de notificação",
            value=cargo_texto,
            inline=False
        )

        embed.add_field(
            name="💬 Mensagem do YouTube",
            value=f"```{mensagem_texto}```",
            inline=False
        )

        embed.add_field(
            name="🛠️ Comandos",
            value=(
                "`/config_canal` → define o canal\n"
                "`/config_cargo` → define o cargo\n"
                "`/config_mensagem` → define a mensagem"
            ),
            inline=False
        )

        embed.set_footer(
            text="Evelly • Sistema de Configuração"
        )

        await interaction.response.send_message(
            embed=embed
        )

    # =====================================================
    # /CONFIG_CANAL
    # =====================================================

    @app_commands.command(
        name="config_canal",
        description="Define o canal onde a Evelly enviará notificações."
    )
    @app_commands.describe(
        canal="Canal que receberá as notificações do YouTube."
    )
    @app_commands.default_permissions(
        administrator=True
    )
    async def config_canal(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                "❌ Este comando só pode ser usado em um servidor.",
                ephemeral=True
            )

            return

        sucesso = configurar_canal_notificacao(
            interaction.guild.id,
            canal.id
        )

        if not sucesso:

            await interaction.response.send_message(
                "❌ Não consegui salvar o canal.",
                ephemeral=True
            )

            return

        embed = discord.Embed(
            title="📢 Canal configurado!",
            description=(
                f"A Evelly enviará as notificações "
                f"do YouTube em {canal.mention}."
            ),
            color=discord.Color.green()
        )

        embed.add_field(
            name="📺 Canal",
            value=canal.mention,
            inline=False
        )

        embed.add_field(
            name="🔔 Importante",
            value=(
                "Verifique se a Evelly possui as permissões "
                "**Ver canal**, **Enviar mensagens** e "
                "**Inserir links**."
            ),
            inline=False
        )

        await interaction.response.send_message(
            embed=embed
        )

    # =====================================================
    # /CONFIG_CANAL_REMOVER
    # =====================================================

    @app_commands.command(
        name="config_canal_remover",
        description="Remove o canal de notificações."
    )
    @app_commands.default_permissions(
        administrator=True
    )
    async def config_canal_remover(
        self,
        interaction: discord.Interaction
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                "❌ Este comando só pode ser usado em um servidor.",
                ephemeral=True
            )

            return

        sucesso = remover_canal_notificacao(
            interaction.guild.id
        )

        if sucesso:

            await interaction.response.send_message(
                "✅ Canal de notificações removido."
            )

        else:

            await interaction.response.send_message(
                "❌ Não consegui remover o canal.",
                ephemeral=True
            )

    # =====================================================
    # /CONFIG_CARGO
    # =====================================================

    @app_commands.command(
        name="config_cargo",
        description="Define o cargo que será mencionado nas notificações."
    )
    @app_commands.describe(
        cargo="Cargo que a Evelly mencionará."
    )
    @app_commands.default_permissions(
        administrator=True
    )
    async def config_cargo(
        self,
        interaction: discord.Interaction,
        cargo: discord.Role
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                "❌ Este comando só pode ser usado em um servidor.",
                ephemeral=True
            )

            return

        sucesso = configurar_cargo_notificacao(
            interaction.guild.id,
            cargo.id
        )

        if not sucesso:

            await interaction.response.send_message(
                "❌ Não consegui salvar o cargo.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            f"✅ O cargo {cargo.mention} agora será "
            "mencionado nas notificações do YouTube."
        )

    # =====================================================
    # /CONFIG_CARGO_REMOVER
    # =====================================================

    @app_commands.command(
        name="config_cargo_remover",
        description="Remove o cargo das notificações."
    )
    @app_commands.default_permissions(
        administrator=True
    )
    async def config_cargo_remover(
        self,
        interaction: discord.Interaction
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                "❌ Este comando só pode ser usado em um servidor.",
                ephemeral=True
            )

            return

        sucesso = remover_cargo_notificacao(
            interaction.guild.id
        )

        if sucesso:

            await interaction.response.send_message(
                "✅ Cargo de notificação removido."
            )

        else:

            await interaction.response.send_message(
                "❌ Não consegui remover o cargo.",
                ephemeral=True
            )

    # =====================================================
    # /CONFIG_MENSAGEM
    # =====================================================

    @app_commands.command(
        name="config_mensagem",
        description="Define a mensagem personalizada do YouTube."
    )
    @app_commands.describe(
        mensagem="Mensagem que será enviada junto da notificação."
    )
    @app_commands.default_permissions(
        administrator=True
    )
    async def config_mensagem(
        self,
        interaction: discord.Interaction,
        mensagem: str
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                "❌ Este comando só pode ser usado em um servidor.",
                ephemeral=True
            )

            return

        if len(mensagem) > 2000:

            await interaction.response.send_message(
                "❌ A mensagem pode ter no máximo "
                "**2000 caracteres**.",
                ephemeral=True
            )

            return

        sucesso = configurar_mensagem_youtube(
            interaction.guild.id,
            mensagem
        )

        if not sucesso:

            await interaction.response.send_message(
                "❌ Não consegui salvar a mensagem.",
                ephemeral=True
            )

            return

        embed = discord.Embed(
            title="💬 Mensagem configurada!",
            description=(
                "A Evelly usará esta mensagem "
                "nas próximas notificações:"
            ),
            color=discord.Color.green()
        )

        embed.add_field(
            name="Mensagem",
            value=mensagem,
            inline=False
        )

        embed.add_field(
            name="🔤 Variáveis disponíveis",
            value=(
                "`{canal}` → nome do canal\n"
                "`{video}` → link do vídeo\n"
                "`{video_id}` → ID do vídeo"
            ),
            inline=False
        )

        await interaction.response.send_message(
            embed=embed
        )

    # =====================================================
    # /CONFIG_MENSAGEM_REMOVER
    # =====================================================

    @app_commands.command(
        name="config_mensagem_remover",
        description="Volta para a mensagem padrão da Evelly."
    )
    @app_commands.default_permissions(
        administrator=True
    )
    async def config_mensagem_remover(
        self,
        interaction: discord.Interaction
    ):

        if interaction.guild is None:

            await interaction.response.send_message(
                "❌ Este comando só pode ser usado em um servidor.",
                ephemeral=True
            )

            return

        sucesso = remover_mensagem_youtube(
            interaction.guild.id
        )

        if sucesso:

            await interaction.response.send_message(
                "✅ Mensagem personalizada removida.\n"
                "A Evelly voltará a usar a mensagem padrão."
            )

        else:

            await interaction.response.send_message(
                "❌ Não consegui remover a mensagem.",
                ephemeral=True
            )


async def setup(bot):

    await bot.add_cog(
        Configuracao(bot)
    )