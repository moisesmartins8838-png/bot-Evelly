# ============================================================
# EVELLY • ENVIAR PV
# ============================================================
#
# Comandos:
#
# /enviarpv usuario:@Pessoa mensagem:"Olá!"
#     -> envia para uma única pessoa.
#
# /enviarpvtodos mensagem:"Olá, pessoal!"
#     -> envia para os membros do servidor.
#
# ============================================================

import asyncio
import time
import traceback

import discord
from discord import app_commands
from discord.ext import commands


# ============================================================
# CONFIGURAÇÕES
# ============================================================

MAX_MESSAGE_LENGTH = 2000

# Intervalo entre DMs no envio em massa.
# Evita tentar enviar centenas de mensagens de uma vez.
DM_DELAY = 1.0


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
    # ENVIO INDIVIDUAL
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
        # AVISO
        # ====================================================

        await self.responder(
            interaction,
            "⏳ Enviando sua mensagem privada..."
        )


        # ====================================================
        # CRIAR EMBED
        # ====================================================

        try:

            embed = self.criar_embed(mensagem)

        except Exception as erro:

            print(
                "❌ [ENVIARPV] Erro criando embed:",
                erro,
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


        except discord.Forbidden:

            await self.editar_resposta(
                interaction,
                (
                    f"❌ Não consegui enviar uma DM para "
                    f"**{usuario.display_name}**.\n\n"
                    "O usuário provavelmente bloqueou DMs "
                    "ou possui alguma configuração que impede "
                    "o recebimento."
                )
            )

            print(
                f"⚠️ [ENVIARPV] DM bloqueada: {usuario} "
                f"({usuario.id})",
                flush=True
            )

            return


        except discord.NotFound:

            await self.editar_resposta(
                interaction,
                "❌ Não consegui encontrar o usuário."
            )

            return


        except discord.HTTPException as erro:

            print(
                "❌ [ENVIARPV] Erro HTTP:",
                erro,
                flush=True
            )

            await self.editar_resposta(
                interaction,
                "❌ O Discord recusou o envio da mensagem privada."
            )

            return


        except Exception as erro:

            print(
                "❌ [ENVIARPV] Erro inesperado:",
                erro,
                flush=True
            )

            traceback.print_exc()

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
        # LOG
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
            f"🆔 ID: {usuario.id}",
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
    # /ENVIARPVTODOS
    # ENVIO PARA TODOS OS MEMBROS
    # ========================================================

    @app_commands.command(
        name="enviarpvtodos",
        description="Envia uma mensagem privada para os membros do servidor."
    )
    @app_commands.describe(
        mensagem="Mensagem que será enviada nas DMs."
    )
    async def enviarpvtodos(
        self,
        interaction: discord.Interaction,
        mensagem: str
    ):

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
        # PERMISSÃO
        # ====================================================

        if not pode_enviar_pv(interaction):

            await self.responder(
                interaction,
                "❌ Você não possui permissão para usar este comando."
            )

            return


        # ====================================================
        # MENSAGEM
        # ====================================================

        mensagem = mensagem.strip()

        if not mensagem:

            await self.responder(
                interaction,
                "❌ A mensagem não pode estar vazia."
            )

            return


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
        # CRIAR EMBED
        # ====================================================

        try:

            embed = self.criar_embed(mensagem)

        except Exception as erro:

            print(
                f"❌ [ENVIARPVTODOS] Erro criando embed: {erro}",
                flush=True
            )

            await self.responder(
                interaction,
                "❌ Não consegui preparar a mensagem."
            )

            return


        # ====================================================
        # PEGAR MEMBROS
        # ====================================================

        membros = [
            membro
            for membro in interaction.guild.members
            if not membro.bot
        ]


        total = len(membros)


        if total == 0:

            await self.responder(
                interaction,
                "❌ Não encontrei membros para enviar a mensagem."
            )

            return


        # ====================================================
        # CONFIRMAR INÍCIO
        # ====================================================

        await self.responder(
            interaction,
            (
                "📨 **ENVIO DE PV INICIADO**\n\n"
                f"👥 Membros encontrados: **{total}**\n"
                "⏳ A Evelly está processando os envios...\n\n"
                "⚠️ Usuários com DMs fechadas serão ignorados."
            )
        )


        inicio = time.monotonic()


        # ====================================================
        # CONTADORES
        # ====================================================

        enviados = 0
        bloqueados = 0
        erros = 0


        # ====================================================
        # ENVIAR PARA CADA MEMBRO
        # ====================================================

        for indice, membro in enumerate(membros, start=1):

            try:

                await membro.send(
                    embed=embed
                )

                enviados += 1


            except discord.Forbidden:

                bloqueados += 1


            except discord.NotFound:

                erros += 1


            except discord.HTTPException as erro:

                erros += 1

                print(
                    f"⚠️ [ENVIARPVTODOS] HTTP "
                    f"{membro} ({membro.id}): {erro}",
                    flush=True
                )


            except Exception as erro:

                erros += 1

                print(
                    f"❌ [ENVIARPVTODOS] Erro "
                    f"{membro} ({membro.id}): {erro}",
                    flush=True
                )


            # ------------------------------------------------
            # Pequeno intervalo entre mensagens.
            # ------------------------------------------------

            await asyncio.sleep(
                DM_DELAY
            )


        # ====================================================
        # TEMPO
        # ====================================================

        duracao = (
            time.monotonic()
            - inicio
        )


        minutos = int(
            duracao // 60
        )

        segundos = int(
            duracao % 60
        )


        # ====================================================
        # RESULTADO
        # ====================================================

        resultado = (
            "📨 **ENVIO DE PV CONCLUÍDO**\n\n"

            f"👥 Total: **{total}**\n"

            f"✅ Enviadas: **{enviados}**\n"

            f"🔒 DMs fechadas: **{bloqueados}**\n"

            f"❌ Erros: **{erros}**\n\n"

            f"⏱️ Duração: "
            f"**{minutos}m {segundos}s**"
        )


        await self.editar_resposta(
            interaction,
            resultado
        )


        # ====================================================
        # LOG TERMINAL
        # ====================================================

        print(
            "==============================================",
            flush=True
        )

        print(
            "📨 EVELLY • ENVIARPVTODOS",
            flush=True
        )

        print(
            f"👤 Executor: {interaction.user}",
            flush=True
        )

        print(
            f"🆔 Executor ID: {interaction.user.id}",
            flush=True
        )

        print(
            f"🏠 Servidor: {interaction.guild.name}",
            flush=True
        )

        print(
            f"🆔 Guild ID: {interaction.guild.id}",
            flush=True
        )

        print(
            f"👥 Total: {total}",
            flush=True
        )

        print(
            f"✅ Enviadas: {enviados}",
            flush=True
        )

        print(
            f"🔒 Bloqueadas: {bloqueados}",
            flush=True
        )

        print(
            f"❌ Erros: {erros}",
            flush=True
        )

        print(
            f"⏱️ Duração: {minutos}m {segundos}s",
            flush=True
        )

        print(
            "==============================================",
            flush=True
        )


    # ========================================================
    # CRIAR EMBED
    # ========================================================

    def criar_embed(
        self,
        mensagem: str
    ) -> discord.Embed:

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


        return embed


    # ========================================================
    # SISTEMA SEGURO DE RESPOSTA
    # ========================================================

    async def responder(
        self,
        interaction: discord.Interaction,
        texto: str
    ):

        try:

            if not interaction.response.is_done():

                await interaction.response.send_message(
                    texto,
                    ephemeral=True
                )

                return


            await interaction.followup.send(
                texto,
                ephemeral=True
            )


        except discord.InteractionResponded:

            print(
                "⚠️ [ENVIARPV] Interaction já respondida.",
                flush=True
            )


        except discord.NotFound:

            print(
                "⚠️ [ENVIARPV] Interaction expirou.",
                flush=True
            )


        except discord.HTTPException as erro:

            print(
                f"⚠️ [ENVIARPV] Erro HTTP: {erro}",
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

            if not interaction.response.is_done():

                await interaction.response.send_message(
                    texto,
                    ephemeral=True
                )

                return


            try:

                await interaction.edit_original_response(
                    content=texto
                )

                return


            except discord.NotFound:

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
                "⚠️ [ENVIARPV] Resposta não encontrada.",
                flush=True
            )


        except discord.HTTPException as erro:

            print(
                f"⚠️ [ENVIARPV] Erro HTTP: {erro}",
                flush=True
            )


        except Exception as erro:

            print(
                f"⚠️ [ENVIARPV] Erro inesperado: {erro}",
                flush=True
            )


# ============================================================
# SETUP
# ============================================================

async def setup(
    bot: commands.Bot
):

    await bot.add_cog(
        EnviarPVCog(bot)
    )

    print(
        "📨 cogs.enviarpv carregado com sucesso.",
        flush=True
    )