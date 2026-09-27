import discord
from discord import app_commands
from discord.ext import commands

from cogs.permissoes import pode_controlar_evelly


DEFAULT_COLOR = 0x8E44AD


class Embed(commands.GroupCog, group_name="embed", group_description="Cria e envia embeds personalizados."):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        print("🖼️ Sistema /embed carregado com sucesso.", flush=True)

    @staticmethod
    def parse_color(cor: str | None) -> int:
        """
        Converte:
        #8E44AD
        8E44AD
        0x8E44AD

        para inteiro.
        """

        if not cor:
            return DEFAULT_COLOR

        valor = cor.strip()

        if valor.startswith("#"):
            valor = valor[1:]

        if valor.lower().startswith("0x"):
            valor = valor[2:]

        if len(valor) != 6:
            raise ValueError(
                "A cor precisa ter exatamente 6 caracteres hexadecimais."
            )

        try:
            numero = int(valor, 16)
        except ValueError:
            raise ValueError(
                "Cor inválida. Use um formato como `#8E44AD`."
            )

        if not 0 <= numero <= 0xFFFFFF:
            raise ValueError("A cor está fora do intervalo permitido.")

        return numero

    @staticmethod
    def build_embed(
        titulo: str,
        mensagem: str,
        cor: int,
        imagem: str | None = None,
        url: str | None = None,
        footer: str | None = None,
    ) -> discord.Embed:

        embed = discord.Embed(
            title=titulo,
            description=mensagem,
            color=discord.Color(cor),
        )

        # URL clicável no título
        if url:
            embed.url = url

        # Imagem / GIF
        if imagem:
            embed.set_image(url=imagem)

        # Footer
        if footer:
            embed.set_footer(text=footer)

        return embed

    @app_commands.command(
        name="criar",
        description="Cria e envia um embed personalizado.",
    )
    @app_commands.describe(
        canal="Canal onde o embed será enviado.",
        titulo="Título do embed.",
        mensagem="Mensagem/descrição do embed.",
        cor="Cor hexadecimal. Exemplo: #8E44AD.",
        imagem="URL da imagem ou GIF.",
        url="URL que será aberta ao clicar no título.",
        footer="Texto opcional no rodapé.",
    )
    async def criar(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel,
        titulo: str,
        mensagem: str,
        cor: str | None = None,
        imagem: str | None = None,
        url: str | None = None,
        footer: str | None = None,
    ):
        # Verifica servidor
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ Este comando só pode ser usado em um servidor.",
                ephemeral=True,
            )
            return

        # Verifica permissão
        if not pode_controlar_evelly(interaction.user):
            await interaction.response.send_message(
                "❌ Você não possui permissão para controlar a Evelly.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        # Validação do título
        if len(titulo) > 256:
            await interaction.followup.send(
                "❌ O título pode ter no máximo **256 caracteres**.",
                ephemeral=True,
            )
            return

        # Validação da mensagem
        if len(mensagem) > 4096:
            await interaction.followup.send(
                "❌ A mensagem pode ter no máximo **4096 caracteres**.",
                ephemeral=True,
            )
            return

        # Validação do footer
        if footer and len(footer) > 2048:
            await interaction.followup.send(
                "❌ O footer pode ter no máximo **2048 caracteres**.",
                ephemeral=True,
            )
            return

        # Validação de URLs
        if imagem and not (
            imagem.startswith("http://")
            or imagem.startswith("https://")
        ):
            await interaction.followup.send(
                "❌ A URL da imagem precisa começar com `http://` ou `https://`.",
                ephemeral=True,
            )
            return

        if url and not (
            url.startswith("http://")
            or url.startswith("https://")
        ):
            await interaction.followup.send(
                "❌ A URL precisa começar com `http://` ou `https://`.",
                ephemeral=True,
            )
            return

        # Converte a cor
        try:
            color_value = self.parse_color(cor)
        except ValueError as e:
            await interaction.followup.send(
                f"❌ {e}",
                ephemeral=True,
            )
            return

        # Cria o embed
        embed = self.build_embed(
            titulo=titulo,
            mensagem=mensagem,
            cor=color_value,
            imagem=imagem,
            url=url,
            footer=footer,
        )

        try:
            mensagem_enviada = await canal.send(
                embed=embed,
                allowed_mentions=discord.AllowedMentions.none(),
            )

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Não tenho permissão para enviar mensagens nesse canal.",
                ephemeral=True,
            )
            return

        except discord.HTTPException as e:
            print(
                f"[EMBED] Erro ao enviar embed: {e}",
                flush=True,
            )

            await interaction.followup.send(
                "❌ O Discord recusou o envio do embed.",
                ephemeral=True,
            )
            return

        # Confirmação
        confirmacao = discord.Embed(
            title="✅ Embed enviado!",
            description=(
                f"O embed foi enviado com sucesso em {canal.mention}.\n\n"
                f"**Mensagem:** [Abrir mensagem]({mensagem_enviada.jump_url})"
            ),
            color=discord.Color(color_value),
        )

        confirmacao.set_footer(
            text="Evelly • Sistema de Embeds"
        )

        await interaction.followup.send(
            embed=confirmacao,
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Embed(bot))