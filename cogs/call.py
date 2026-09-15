import asyncio
import time
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands


TEMPO_MINIMO = 1
TEMPO_MAXIMO = 1440


class Call(commands.GroupCog, group_name="call"):
    """
    Sistema de call da Evelly.

    Comandos:

    /call entrar
    /call sair
    /call status
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # Tarefa responsável por retirar a Evelly da call.
        self.tarefas_saida: dict[int, asyncio.Task] = {}

        # Timestamp Unix em que a Evelly deverá sair.
        self.saidas: dict[int, float] = {}

    # ============================================================
    # FUNÇÕES AUXILIARES
    # ============================================================

    def cancelar_tarefa(self, guild_id: int):
        """
        Cancela uma tarefa de saída existente.
        """

        tarefa = self.tarefas_saida.pop(guild_id, None)

        if tarefa and not tarefa.done():
            tarefa.cancel()

        self.saidas.pop(guild_id, None)

    async def desconectar_automaticamente(
        self,
        guild_id: int,
        segundos: int
    ):
        """
        Aguarda o tempo configurado e desconecta a Evelly.
        """

        try:
            await asyncio.sleep(segundos)

            guild = self.bot.get_guild(guild_id)

            if guild is None:
                return

            voice = guild.voice_client

            if voice is not None:
                try:
                    await voice.disconnect(force=True)
                except Exception as erro:
                    print(
                        f"[CALL] Erro ao desconectar automaticamente "
                        f"do servidor {guild_id}: {erro}",
                        flush=True
                    )

            self.saidas.pop(guild_id, None)
            self.tarefas_saida.pop(guild_id, None)

            print(
                f"[CALL] Evelly saiu automaticamente da call "
                f"(Guild ID: {guild_id})",
                flush=True
            )

        except asyncio.CancelledError:
            return

        except Exception as erro:
            print(
                f"[CALL] Erro na tarefa automática: {erro}",
                flush=True
            )

            self.saidas.pop(guild_id, None)
            self.tarefas_saida.pop(guild_id, None)

    def formatar_tempo(self, segundos: int) -> str:
        """
        Formata segundos para uma apresentação amigável.
        """

        segundos = max(0, int(segundos))

        minutos, segundos_restantes = divmod(segundos, 60)

        horas, minutos = divmod(minutos, 60)

        partes = []

        if horas:
            partes.append(
                f"{horas}h"
            )

        if minutos:
            partes.append(
                f"{minutos}min"
            )

        if segundos_restantes or not partes:
            partes.append(
                f"{segundos_restantes}s"
            )

        return " ".join(partes)

    # ============================================================
    # /CALL ENTRAR
    # ============================================================

    @app_commands.command(
        name="entrar",
        description="Coloca a Evelly em uma call por um tempo determinado."
    )
    @app_commands.describe(
        canal="Canal de voz onde a Evelly deve entrar.",
        tempo="Tempo em minutos que a Evelly ficará na call."
    )
    async def entrar(
        self,
        interaction: discord.Interaction,
        canal: discord.VoiceChannel,
        tempo: app_commands.Range[int, 1, 1440]
    ):
        """
        Entra ou move a Evelly para um canal de voz.
        """

        # --------------------------------------------------------
        # Verificar servidor
        # --------------------------------------------------------

        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Esse comando só pode ser usado em um servidor.",
                ephemeral=True
            )
            return

        guild = interaction.guild
        guild_id = guild.id

        # --------------------------------------------------------
        # Verificar permissões do bot
        # --------------------------------------------------------

        me = guild.me

        if me is None:
            await interaction.response.send_message(
                "❌ Não consegui identificar a Evelly neste servidor.",
                ephemeral=True
            )
            return

        permissoes = canal.permissions_for(me)

        if not permissoes.view_channel:
            await interaction.response.send_message(
                "❌ Eu não tenho permissão para visualizar esse canal.",
                ephemeral=True
            )
            return

        if not permissoes.connect:
            await interaction.response.send_message(
                "❌ Eu não tenho permissão para entrar nesse canal de voz.",
                ephemeral=True
            )
            return

        # --------------------------------------------------------
        # Responder imediatamente
        # --------------------------------------------------------

        await interaction.response.defer()

        try:

            # ----------------------------------------------------
            # Tempo
            # ----------------------------------------------------

            minutos = int(tempo)

            if minutos < TEMPO_MINIMO:
                minutos = TEMPO_MINIMO

            if minutos > TEMPO_MAXIMO:
                minutos = TEMPO_MAXIMO

            segundos = minutos * 60

            # ----------------------------------------------------
            # Cancelar contador anterior
            # ----------------------------------------------------

            self.cancelar_tarefa(guild_id)

            # ----------------------------------------------------
            # Verificar conexão atual
            # ----------------------------------------------------

            voice = guild.voice_client

            if voice is not None:

                # Se já está no mesmo canal.
                if voice.channel.id == canal.id:

                    novo_fim = time.time() + segundos

                    self.saidas[guild_id] = novo_fim

                    tarefa = asyncio.create_task(
                        self.desconectar_automaticamente(
                            guild_id,
                            segundos
                        )
                    )

                    self.tarefas_saida[guild_id] = tarefa

                    await interaction.followup.send(
                        (
                            "🔄 **Tempo da call atualizado!**\n\n"
                            f"📞 Canal: {canal.mention}\n"
                            f"⏱️ Tempo: **{minutos} minuto(s)**\n"
                            f"🕐 Saída prevista: "
                            f"<t:{int(novo_fim)}:R>"
                        )
                    )

                    return

                # Caso esteja em outro canal, move.
                try:
                    await voice.move_to(canal)

                except Exception as erro:
                    print(
                        f"[CALL] Erro ao mover Evelly: {erro}",
                        flush=True
                    )

                    await interaction.followup.send(
                        (
                            "❌ Não consegui mover a Evelly "
                            "para esse canal."
                        ),
                        ephemeral=True
                    )

                    return

            else:

                # ------------------------------------------------
                # Entrar na call
                # ------------------------------------------------

                try:
                    await canal.connect(
                        self_deaf=True
                    )

                except discord.Forbidden:
                    await interaction.followup.send(
                        (
                            "❌ O Discord negou a entrada da Evelly "
                            "nesse canal.\n\n"
                            "Verifique a permissão **Conectar**."
                        ),
                        ephemeral=True
                    )
                    return

                except discord.ClientException as erro:
                    print(
                        f"[CALL] ClientException ao conectar: {erro}",
                        flush=True
                    )

                    await interaction.followup.send(
                        (
                            "❌ Não consegui conectar a Evelly "
                            "ao canal de voz."
                        ),
                        ephemeral=True
                    )
                    return

                except Exception as erro:
                    print(
                        f"[CALL] Erro ao conectar na call: {erro}",
                        flush=True
                    )

                    await interaction.followup.send(
                        (
                            "❌ Ocorreu um erro ao entrar na call."
                        ),
                        ephemeral=True
                    )
                    return

            # ----------------------------------------------------
            # Criar contador
            # ----------------------------------------------------

            fim = time.time() + segundos

            self.saidas[guild_id] = fim

            tarefa = asyncio.create_task(
                self.desconectar_automaticamente(
                    guild_id,
                    segundos
                )
            )

            self.tarefas_saida[guild_id] = tarefa

            # ----------------------------------------------------
            # Mensagem
            # ----------------------------------------------------

            await interaction.followup.send(
                (
                    "📞 **Evelly entrou na call!**\n\n"
                    f"🔊 Canal: {canal.mention}\n"
                    f"⏱️ Permanência: **{minutos} minuto(s)**\n"
                    f"🕐 Saída prevista: "
                    f"<t:{int(fim)}:R>\n\n"
                    "🔇 A Evelly está conectada sem reproduzir áudio."
                )
            )

            print(
                f"[CALL] Evelly entrou em '{canal.name}' "
                f"por {minutos} minuto(s).",
                flush=True
            )

        except Exception as erro:

            print(
                f"[CALL] Erro no /call entrar: {erro}",
                flush=True
            )

            await interaction.followup.send(
                "❌ Ocorreu um erro ao colocar a Evelly na call.",
                ephemeral=True
            )

    # ============================================================
    # /CALL SAIR
    # ============================================================

    @app_commands.command(
        name="sair",
        description="Retira a Evelly da call imediatamente."
    )
    async def sair(
        self,
        interaction: discord.Interaction
    ):

        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Esse comando só pode ser usado em um servidor.",
                ephemeral=True
            )
            return

        guild = interaction.guild
        guild_id = guild.id

        voice = guild.voice_client

        if voice is None:
            self.cancelar_tarefa(guild_id)

            await interaction.response.send_message(
                "ℹ️ A Evelly não está em nenhuma call.",
                ephemeral=True
            )
            return

        canal_nome = voice.channel.name

        self.cancelar_tarefa(guild_id)

        try:
            await voice.disconnect(force=True)

        except Exception as erro:
            print(
                f"[CALL] Erro ao sair da call: {erro}",
                flush=True
            )

            await interaction.response.send_message(
                "❌ Não consegui desconectar da call.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            (
                "👋 **Evelly saiu da call.**\n"
                f"📞 Canal: **{canal_nome}**"
            )
        )

        print(
            f"[CALL] Evelly saiu manualmente da call "
            f"(Guild ID: {guild_id})",
            flush=True
        )

    # ============================================================
    # /CALL STATUS
    # ============================================================

    @app_commands.command(
        name="status",
        description="Mostra o status atual da Evelly na call."
    )
    async def status(
        self,
        interaction: discord.Interaction
    ):

        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Esse comando só pode ser usado em um servidor.",
                ephemeral=True
            )
            return

        guild = interaction.guild
        guild_id = guild.id

        voice = guild.voice_client

        if voice is None:
            await interaction.response.send_message(
                (
                    "🔇 **Evelly não está em uma call.**\n\n"
                    "Use `/call entrar` para colocá-la em um canal."
                )
            )
            return

        agora = time.time()

        fim = self.saidas.get(guild_id)

        if fim is None:
            await interaction.response.send_message(
                (
                    "📞 **Evelly está em uma call.**\n\n"
                    f"🔊 Canal: {voice.channel.mention}\n"
                    "⏱️ Tempo automático: não configurado."
                )
            )
            return

        restante = max(
            0,
            int(fim - agora)
        )

        if restante <= 0:
            restante_texto = "saindo agora"

        else:
            restante_texto = self.formatar_tempo(
                restante
            )

        await interaction.response.send_message(
            (
                "📞 **Status da Evelly**\n\n"
                f"🔊 Canal: {voice.channel.mention}\n"
                f"⏱️ Tempo restante: **{restante_texto}**\n"
                f"🕐 Saída: <t:{int(fim)}:R>\n"
                "🔇 Áudio: desativado"
            )
        )

    # ============================================================
    # DESCARREGAR COG
    # ============================================================

    def cog_unload(self):

        for tarefa in self.tarefas_saida.values():

            if not tarefa.done():
                tarefa.cancel()

        self.tarefas_saida.clear()
        self.saidas.clear()


async def setup(bot: commands.Bot):

    await bot.add_cog(
        Call(bot)
    )