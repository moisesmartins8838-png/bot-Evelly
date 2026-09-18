import discord
from discord.ext import commands
from discord import app_commands

from database.database import (
    configurar_call_auto,
    desativar_call_auto,
    pegar_call_auto,
    pegar_todos_call_auto,
)

from cogs.permissoes import pode_controlar_evelly


class CallAuto(
    commands.GroupCog,
    group_name="callauto",
    group_description="Entrada automática em canal de voz",
):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self._inicializacao_executada = False
        self._inicializacao_lock = False

    # ============================================================
    # CONECTAR UM SERVIDOR
    # ============================================================

    async def conectar_servidor(self, guild_id: int, channel_id: int):

        guild = self.bot.get_guild(int(guild_id))

        if guild is None:
            print(
                f"[CALLAUTO] Servidor {guild_id} não está disponível."
            )
            return False

        canal = guild.get_channel(int(channel_id))

        if canal is None:
            print(
                f"[CALLAUTO] Canal {channel_id} não encontrado "
                f"no servidor {guild.name}."
            )
            return False

        if not isinstance(canal, discord.VoiceChannel):
            print(
                f"[CALLAUTO] O canal configurado não é um canal de voz: "
                f"{canal.name}"
            )
            return False

        # --------------------------------------------------------
        # PERMISSÕES
        # --------------------------------------------------------

        me = guild.me

        if me is None:
            print(
                f"[CALLAUTO] Não foi possível encontrar a Evelly "
                f"no servidor {guild.name}."
            )
            return False

        permissoes = canal.permissions_for(me)

        if not permissoes.view_channel:
            print(
                f"[CALLAUTO] Evelly não possui permissão para visualizar "
                f"o canal {canal.name}."
            )
            return False

        if not permissoes.connect:
            print(
                f"[CALLAUTO] Evelly não possui permissão para entrar "
                f"no canal {canal.name}."
            )
            return False

        # --------------------------------------------------------
        # VERIFICAR CONEXÃO EXISTENTE
        # --------------------------------------------------------

        voice = guild.voice_client

        try:

            if voice is not None:

                if voice.is_connected():

                    if voice.channel.id == canal.id:
                        print(
                            f"[CALLAUTO] Evelly já está no canal "
                            f"{canal.name} • {guild.name}"
                        )
                        return True

                    print(
                        f"[CALLAUTO] Movendo Evelly para "
                        f"{canal.name} • {guild.name}"
                    )

                    await voice.move_to(canal)

                    print(
                        f"[CALLAUTO] Evelly conectada em "
                        f"{canal.name} • {guild.name}"
                    )

                    return True

                try:
                    await voice.disconnect(force=True)
                except Exception:
                    pass

            # ----------------------------------------------------
            # NOVA CONEXÃO
            # ----------------------------------------------------

            print(
                f"[CALLAUTO] Entrando automaticamente em "
                f"{canal.name} • {guild.name}"
            )

            await canal.connect(self_deaf=True)

            print(
                f"[CALLAUTO] Evelly conectada em "
                f"{canal.name} • {guild.name}"
            )

            return True

        except discord.Forbidden:
            print(
                f"[CALLAUTO] Sem permissão para conectar em "
                f"{canal.name} • {guild.name}"
            )
            return False

        except discord.ClientException as erro:
            print(
                f"[CALLAUTO] Erro de conexão em "
                f"{guild.name}: {erro}"
            )
            return False

        except Exception as erro:
            print(
                f"[CALLAUTO] Erro inesperado em "
                f"{guild.name}: {erro}"
            )
            return False

    # ============================================================
    # CONECTAR TODOS OS SERVIDORES CONFIGURADOS
    # ============================================================

    async def conectar_todos(self):

        configuracoes = pegar_todos_call_auto()

        if not configuracoes:
            print(
                "[CALLAUTO] Nenhum servidor configurado "
                "para entrada automática."
            )
            return

        print(
            f"[CALLAUTO] Encontradas {len(configuracoes)} "
            f"configuração(ões) automática(s)."
        )

        for guild_id, channel_id, enabled in configuracoes:

            if not enabled:
                continue

            try:

                await self.conectar_servidor(
                    int(guild_id),
                    int(channel_id),
                )

            except Exception as erro:

                print(
                    f"[CALLAUTO] Erro conectando servidor "
                    f"{guild_id}: {erro}"
                )

    # ============================================================
    # INICIALIZAÇÃO
    # ============================================================

    async def inicializar_callauto(self):

        if self._inicializacao_executada:
            return

        if self._inicializacao_lock:
            return

        self._inicializacao_lock = True

        try:

            print(
                "[CALLAUTO] Inicializando sistema "
                "de entrada automática..."
            )

            await self.conectar_todos()

            self._inicializacao_executada = True

            print(
                "[CALLAUTO] Inicialização concluída."
            )

        except Exception as erro:

            print(
                f"[CALLAUTO] Erro durante inicialização: {erro}"
            )

        finally:

            self._inicializacao_lock = False

    # ============================================================
    # EVENTO READY
    # ============================================================

    @commands.Cog.listener()
    async def on_ready(self):

        await self.inicializar_callauto()

    # ============================================================
    # /callauto ativar
    # ============================================================

    @app_commands.command(
        name="ativar",
        description="Ativa a entrada automática em um canal.",
    )
    @app_commands.describe(
        canal="Canal de voz onde a Evelly deverá entrar automaticamente."
    )
    async def ativar(
        self,
        interaction: discord.Interaction,
        canal: discord.VoiceChannel,
    ):

        if not pode_controlar_evelly(interaction.user):

            await interaction.response.send_message(
                "❌ Você não possui permissão para configurar a Evelly.",
                ephemeral=True,
            )
            return

        guild = interaction.guild

        if guild is None:

            await interaction.response.send_message(
                "❌ Este comando só pode ser usado dentro de um servidor.",
                ephemeral=True,
            )
            return

        me = guild.me

        if me is None:

            await interaction.response.send_message(
                "❌ Não consegui verificar minhas permissões.",
                ephemeral=True,
            )
            return

        permissoes = canal.permissions_for(me)

        if not permissoes.view_channel:

            await interaction.response.send_message(
                "❌ Eu não tenho permissão para visualizar esse canal.",
                ephemeral=True,
            )
            return

        if not permissoes.connect:

            await interaction.response.send_message(
                "❌ Eu não tenho permissão para entrar nesse canal.",
                ephemeral=True,
            )
            return

        sucesso = configurar_call_auto(
            guild.id,
            canal.id,
        )

        if not sucesso:

            await interaction.response.send_message(
                "❌ Não foi possível salvar a configuração no Supabase.",
                ephemeral=True,
            )
            return

        conectado = await self.conectar_servidor(
            guild.id,
            canal.id,
        )

        if conectado:

            await interaction.response.send_message(
                f"✅ **CallAuto ativado!**\n\n"
                f"📞 Canal: {canal.mention}\n"
                f"🔄 A Evelly entrará automaticamente nesse canal "
                f"sempre que iniciar ou reiniciar.",
                ephemeral=True,
            )

        else:

            await interaction.response.send_message(
                f"⚠️ **CallAuto configurado!**\n\n"
                f"📞 Canal: {canal.mention}\n\n"
                f"Não consegui entrar no canal agora. "
                f"Verifique minhas permissões.",
                ephemeral=True,
            )

    # ============================================================
    # /callauto desativar
    # ============================================================

    @app_commands.command(
        name="desativar",
        description="Desativa a entrada automática.",
    )
    async def desativar(
        self,
        interaction: discord.Interaction,
    ):

        if not pode_controlar_evelly(interaction.user):

            await interaction.response.send_message(
                "❌ Você não possui permissão para configurar a Evelly.",
                ephemeral=True,
            )
            return

        guild = interaction.guild

        if guild is None:

            await interaction.response.send_message(
                "❌ Este comando só pode ser usado dentro de um servidor.",
                ephemeral=True,
            )
            return

        sucesso = desativar_call_auto(guild.id)

        if not sucesso:

            await interaction.response.send_message(
                "❌ Não foi possível desativar o CallAuto.",
                ephemeral=True,
            )
            return

        voice = guild.voice_client

        if voice is not None and voice.is_connected():

            try:
                await voice.disconnect(force=True)
            except Exception as erro:
                print(
                    f"[CALLAUTO] Erro desconectando Evelly: {erro}"
                )

        await interaction.response.send_message(
            "🔴 **CallAuto desativado!**\n\n"
            "A Evelly não entrará mais automaticamente em "
            "um canal de voz após reiniciar.",
            ephemeral=True,
        )

    # ============================================================
    # /callauto status
    # ============================================================

    @app_commands.command(
        name="status",
        description="Mostra o status do CallAuto.",
    )
    async def status(
        self,
        interaction: discord.Interaction,
    ):

        if not pode_controlar_evelly(interaction.user):

            await interaction.response.send_message(
                "❌ Você não possui permissão para visualizar "
                "a configuração do CallAuto.",
                ephemeral=True,
            )
            return

        guild = interaction.guild

        if guild is None:

            await interaction.response.send_message(
                "❌ Este comando só pode ser usado dentro de um servidor.",
                ephemeral=True,
            )
            return

        configuracao = pegar_call_auto(guild.id)

        if not configuracao:

            await interaction.response.send_message(
                "ℹ️ **CallAuto não está configurado neste servidor.**",
                ephemeral=True,
            )
            return

        guild_id, channel_id, enabled = configuracao

        canal = guild.get_channel(int(channel_id))

        voice = guild.voice_client

        if enabled:

            status_texto = "🟢 Ativado"

        else:

            status_texto = "🔴 Desativado"

        if canal is not None:

            canal_texto = canal.mention

        else:

            canal_texto = f"`Canal não encontrado ({channel_id})`"

        if voice is not None and voice.is_connected():

            if voice.channel:

                conexao_texto = (
                    f"🟢 Conectada em {voice.channel.mention}"
                )

            else:

                conexao_texto = "🟢 Conectada"

        else:

            conexao_texto = "⚪ Não conectada"

        embed = discord.Embed(
            title="📞 CallAuto • Evelly",
            description=(
                "Configuração da entrada automática "
                "em canal de voz."
            ),
            color=discord.Color.blurple(),
        )

        embed.add_field(
            name="Status",
            value=status_texto,
            inline=False,
        )

        embed.add_field(
            name="Canal configurado",
            value=canal_texto,
            inline=False,
        )

        embed.add_field(
            name="Conexão atual",
            value=conexao_texto,
            inline=False,
        )

        embed.set_footer(
            text="Evelly • CallAuto"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )


# ================================================================
# SETUP
# ================================================================

async def setup(bot: commands.Bot):

    await bot.add_cog(
        CallAuto(bot)
    )