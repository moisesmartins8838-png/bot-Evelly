# ============================================================
# EVELLY • ENVIAR PV
# ============================================================
#
# Comando:
# /enviarpv usuario:@Pessoa mensagem:"Olá!"
#
# Envia uma mensagem privada através da Evelly.
#
# ============================================================

import traceback

import discord
from discord import app_commands
from discord.ext import commands


# ============================================================
# CONFIGURAÇÕES
# ============================================================

MAX_MESSAGE_LENGTH = 2000


# ============================================================
# PERMISSÕES
# ============================================================

def pode_enviar_pv(interaction: discord.Interaction) -> bool:

    if interaction.guild is None:
        return False

    membro = interaction.user

    if not isinstance(membro, discord.Member):
        return False

    permissoes = membro.guild_permissions

    return (
        permissoes.administrator
        or permissoes.manage_guild
        or permissoes.manage_messages
    )


# ============================================================
# COG
# ============================================================

class EnviarPVCog(commands.Cog):

    def __init__(self, bot: commands.Bot):

        self.bot = bot

        print(
            "📨 Sistema EnviarPV carregado com sucesso.",
            flush=True
        )

    # ========================================================
    # /ENVIARPV
    # ========================================================

    @app_commands.command(
        name="enviarpv",
        description="Envia uma mensagem privada para um usuário."
    )
    @app_commands.describe(
        usuario="Usuário que receberá a mensagem.",
        mensagem="Mensagem que será enviada na DM."
    )
    async def enviarpv(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        mensagem: str
    ):

        # ====================================================
        # IMPORTANTE:
        # NÃO fazemos response.send_message() imediatamente.
        #
        # O bot possui handlers globais e, dependendo de como
        # a Interaction chegou, ela pode já ter sido reconhecida.
        #
        # Vamos trabalhar com uma função segura de resposta.
        # ====================================================

        # ====================================================
        # VERIFICAR SERVIDOR
        # ====================================================

        if interaction.guild is None:

            await self.responder(
                interaction,
                "❌ Este comando só pode ser usado dentro de um servidor."
            )

            return

        # ====================================================
        # VERIFICAR PERMISSÃO
        # ====================================================

        if not pode_enviar_pv(interaction):

            await self.responder(
                interaction,
                "❌ Você não possui permissão para usar este comando."
            )

            return

        # ====================================================
        # VERIFICAR BOT
        # ====================================================

        if usuario.bot:

            await self.responder(
                interaction,
                "❌ Não é permitido enviar mensagens privadas para bots."
            )

            return

        # ====================================================
        # LIMPAR MENSAGEM
        # ====================================================

        mensagem = mensagem.strip()

        if not mensagem:

            await self.responder(
                interaction,
                "❌ A mensagem não pode estar vazia."
            )

            return

        # ====================================================
        # LIMITE DO DISCORD
        # ====================================================

        if len(mensagem) > MAX_MESSAGE_LENGTH:

            await self.responder(
                interaction,
                (
                    f"❌ A mensagem pode ter no máximo "
                    f"**{MAX_MESSAGE_LENGTH} caracteres**."
                )
            )

            return

        # ====================================================
        # IMPEDIR ENVIO PARA SI MESMO
        # ====================================================

        if usuario.id == interaction.user.id:

            await self.responder(
                interaction,
                "❌ Você não pode enviar uma mensagem para si mesmo."
            )

            return

        # ====================================================
        # AVISO DE PROCESSAMENTO
        # ====================================================

        await self.responder(
            interaction,
            "⏳ Enviando sua mensagem privada..."
        )

        # ====================================================
        # CRIAR EMBED
        # ====================================================

        try:

            embed = discord.Embed(
                description=mensagem,
                timestamp=discord.utils.utcnow()
            )

            if self.bot.user:

                embed.set_author(
                    name="Evelly",
                    icon_url=self.bot.user.display_avatar.url
                )

            embed.set_footer(
                text="Mensagem enviada pela equipe."
            )

        except Exception as erro:

            print(
                "==============================================",
                flush=True
            )

            print(
                "❌ [ENVIARPV] ERRO CRIANDO EMBED",
                flush=True
            )

            print(
                f"Tipo: {type(erro).__name__}",
                flush=True
            )

            print(
                f"Erro: {erro}",
                flush=True
            )

            traceback.print_exc()

            print(
                "==============================================",
                flush=True
            )

            await self.editar_resposta(
                interaction,
                "❌ Não consegui preparar a mensagem."
            )

            return

        # ====================================================
        # ENVIAR DM
        # ====================================================

        try:

            await usuario.send(
                embed=embed
            )

        # ====================================================
        # DM BLOQUEADA
        # ====================================================

        except discord.Forbidden:

            await self.editar_resposta(
                interaction,
                (
                    f"❌ Não consegui enviar uma DM para "
                    f"**{usuario.display_name}**.\n\n"
                    "O usuário provavelmente bloqueou DMs "
                    "de membros deste servidor ou possui "
                    "alguma configuração que impede o recebimento."
                )
            )

            print(
                "==============================================",
                flush=True
            )

            print(
                "⚠️ [ENVIARPV] DM BLOQUEADA",
                flush=True
            )

            print(
                f"Usuário: {usuario}",
                flush=True
            )

            print(
                f"ID: {usuario.id}",
                flush=True
            )

            print(
                "==============================================",
                flush=True
            )

            return

        # ====================================================
        # USUÁRIO NÃO ENCONTRADO
        # ====================================================

        except discord.NotFound:

            await self.editar_resposta(
                interaction,
                "❌ Não consegui encontrar o usuário."
            )

            return

        # ====================================================
        # ERRO HTTP
        # ====================================================

        except discord.HTTPException as erro:

            print(
                "==============================================",
                flush=True
            )

            print(
                "❌ [ENVIARPV] ERRO HTTP AO ENVIAR DM",
                flush=True
            )

            print(
                f"Status: {erro.status}",
                flush=True
            )

            print(
                f"Erro: {erro}",
                flush=True
            )

            print(
                "==============================================",
                flush=True
            )

            await self.editar_resposta(
                interaction,
                "❌ O Discord recusou o envio da mensagem privada."
            )

            return

        # ====================================================
        # ERRO GERAL
        # ====================================================

        except Exception as erro:

            print(
                "==============================================",
                flush=True
            )

            print(
                "❌ [ENVIARPV] ERRO INESPERADO",
                flush=True
            )

            print(
                f"Tipo: {type(erro).__name__}",
                flush=True
            )

            print(
                f"Erro: {erro}",
                flush=True
            )

            traceback.print_exc()

            print(
                "==============================================",
                flush=True
            )

            await self.editar_resposta(
                interaction,
                "❌ Ocorreu um erro ao enviar a mensagem privada."
            )

            return

        # ====================================================
        # SUCESSO
        # ====================================================

        await self.editar_resposta(
            interaction,
            (
                "✅ **Mensagem enviada com sucesso!**\n\n"
                f"👤 Destinatário: {usuario.mention}\n"
                f"📨 Mensagem: {mensagem}"
            )
        )

        # ====================================================
        # LOG TERMINAL
        # ====================================================

        print(
            "==============================================",
            flush=True
        )

        print(
            "📨 EVELLY • ENVIAR PV",
            flush=True
        )

        print(
            f"👤 Quem enviou: {interaction.user}",
            flush=True
        )

        print(
            f"🎯 Destinatário: {usuario}",
            flush=True
        )

        print(
            f"🆔 ID destinatário: {usuario.id}",
            flush=True
        )

        print(
            f"💬 Mensagem: {mensagem}",
            flush=True
        )

        print(
            "✅ DM enviada com sucesso.",
            flush=True
        )

        print(
            "==============================================",
            flush=True
        )

    # ========================================================
    # SISTEMA SEGURO DE RESPOSTA
    # ========================================================

    async def responder(
        self,
        interaction: discord.Interaction,
        texto: str
    ):

        try:

            # ------------------------------------------------
            # A Interaction ainda não foi reconhecida.
            # ------------------------------------------------

            if not interaction.response.is_done():

                await interaction.response.send_message(
                    texto,
                    ephemeral=True
                )

                return

            # ------------------------------------------------
            # A Interaction JÁ foi reconhecida.
            #
            # Nesse caso NÃO podemos usar:
            #
            # interaction.response.send_message()
            #
            # Usamos followup.
            # ------------------------------------------------

            await interaction.followup.send(
                texto,
                ephemeral=True
            )

        except discord.InteractionResponded:

            print(
                "⚠️ [ENVIARPV] Interaction já havia sido respondida.",
                flush=True
            )

        except discord.NotFound:

            print(
                "⚠️ [ENVIARPV] Interaction expirou.",
                flush=True
            )

        except discord.HTTPException as erro:

            print(
                f"⚠️ [ENVIARPV] Erro HTTP ao responder: {erro}",
                flush=True
            )

        except Exception as erro:

            print(
                f"⚠️ [ENVIARPV] Erro ao responder: {erro}",
                flush=True
            )

    # ========================================================
    # EDITAR RESPOSTA ORIGINAL
    # ========================================================

    async def editar_resposta(
        self,
        interaction: discord.Interaction,
        texto: str
    ):

        try:

            # ------------------------------------------------
            # Se existe uma resposta original criada pela
            # própria Interaction, tentamos editá-la.
            # ------------------------------------------------

            if not interaction.response.is_done():

                await interaction.response.send_message(
                    texto,
                    ephemeral=True
                )

                return

            # ------------------------------------------------
            # Interaction já respondida.
            #
            # Tentamos editar a resposta original.
            # ------------------------------------------------

            try:

                await interaction.edit_original_response(
                    content=texto
                )

                return

            except discord.NotFound:

                # ------------------------------------------------
                # Caso não exista resposta original, enviamos
                # um followup.
                # ------------------------------------------------

                await interaction.followup.send(
                    texto,
                    ephemeral=True
                )

        except discord.InteractionResponded:

            try:

                await interaction.followup.send(
                    texto,
                    ephemeral=True
                )

            except Exception as erro:

                print(
                    f"⚠️ [ENVIARPV] Falha no followup: {erro}",
                    flush=True
                )

        except discord.NotFound:

            print(
                "⚠️ [ENVIARPV] Não foi possível editar/enviar resposta.",
                flush=True
            )

        except discord.HTTPException as erro:

            print(
                f"⚠️ [ENVIARPV] Erro HTTP editando resposta: {erro}",
                flush=True
            )

        except Exception as erro:

            print(
                f"⚠️ [ENVIARPV] Erro inesperado editando resposta: {erro}",
                flush=True
            )


# ============================================================
# SETUP
# ============================================================

async def setup(bot: commands.Bot):

    await bot.add_cog(
        EnviarPVCog(bot)
    )

    print(
        "📨 cogs.enviarpv carregado com sucesso.",
        flush=True
    )