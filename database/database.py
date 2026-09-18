import os

from dotenv import load_dotenv
from supabase import create_client, Client


load_dotenv()


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_PUBLISHABLE_KEY")
)


if not SUPABASE_URL:
    raise RuntimeError(
        "❌ SUPABASE_URL não encontrada no .env"
    )


if not SUPABASE_KEY:
    raise RuntimeError(
        "❌ SUPABASE_PUBLISHABLE_KEY não encontrada no .env"
    )


supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


# =========================================================
# BANCO
# =========================================================

def criar_banco():

    print("☁️ Banco Supabase conectado!")


# =========================================================
# SERVIDOR
# =========================================================

def criar_servidor(guild_id):

    try:

        existente = (
            supabase
            .table("servidores")
            .select("id")
            .eq("id", guild_id)
            .execute()
        )

        if existente.data:
            return

        supabase.table("servidores").insert({
            "id": guild_id
        }).execute()

        print(
            f"☁️ Servidor {guild_id} salvo no Supabase."
        )

    except Exception as erro:

        print(
            f"❌ Erro criando servidor {guild_id}: {erro}"
        )


def pegar_servidor(guild_id):

    try:

        resposta = (
            supabase
            .table("servidores")
            .select("*")
            .eq("id", guild_id)
            .execute()
        )

        if not resposta.data:
            return None

        servidor = resposta.data[0]

        return (
            servidor.get("id"),
            servidor.get("canal_notificacao"),
            servidor.get("cargo_notificacao"),
            servidor.get("mensagem_youtube"),
            servidor.get("youtube_ativo"),
            servidor.get("boas_vindas_ativo"),
            servidor.get("canal_boas_vindas")
        )

    except Exception as erro:

        print(
            f"❌ Erro buscando servidor {guild_id}: {erro}"
        )

        return None


# =========================================================
# CANAL DE NOTIFICAÇÃO
# =========================================================

def configurar_canal_notificacao(
    guild_id,
    canal_id
):

    criar_servidor(guild_id)

    try:

        supabase.table("servidores").update({
            "canal_notificacao": canal_id
        }).eq(
            "id",
            guild_id
        ).execute()

        print(
            f"☁️ Canal de notificação salvo: {canal_id}"
        )

        return True

    except Exception as erro:

        print(
            f"❌ Erro salvando canal: {erro}"
        )

        return False


def remover_canal_notificacao(guild_id):

    criar_servidor(guild_id)

    try:

        supabase.table("servidores").update({
            "canal_notificacao": None
        }).eq(
            "id",
            guild_id
        ).execute()

        print(
            "☁️ Canal de notificação removido."
        )

        return True

    except Exception as erro:

        print(
            f"❌ Erro removendo canal: {erro}"
        )

        return False


# =========================================================
# CARGO DE NOTIFICAÇÃO
# =========================================================

def configurar_cargo_notificacao(
    guild_id,
    cargo_id
):

    criar_servidor(guild_id)

    try:

        supabase.table("servidores").update({
            "cargo_notificacao": cargo_id
        }).eq(
            "id",
            guild_id
        ).execute()

        print(
            f"☁️ Cargo de notificação salvo: {cargo_id}"
        )

        return True

    except Exception as erro:

        print(
            f"❌ Erro salvando cargo: {erro}"
        )

        return False


def remover_cargo_notificacao(guild_id):

    criar_servidor(guild_id)

    try:

        supabase.table("servidores").update({
            "cargo_notificacao": None
        }).eq(
            "id",
            guild_id
        ).execute()

        print(
            "☁️ Cargo de notificação removido."
        )

        return True

    except Exception as erro:

        print(
            f"❌ Erro removendo cargo: {erro}"
        )

        return False


# =========================================================
# MENSAGEM DO YOUTUBE
# =========================================================

def configurar_mensagem_youtube(
    guild_id,
    mensagem
):

    criar_servidor(guild_id)

    try:

        supabase.table("servidores").update({
            "mensagem_youtube": mensagem
        }).eq(
            "id",
            guild_id
        ).execute()

        print(
            "☁️ Mensagem do YouTube salva."
        )

        return True

    except Exception as erro:

        print(
            f"❌ Erro salvando mensagem: {erro}"
        )

        return False


def remover_mensagem_youtube(guild_id):

    criar_servidor(guild_id)

    try:

        supabase.table("servidores").update({
            "mensagem_youtube": None
        }).eq(
            "id",
            guild_id
        ).execute()

        print(
            "☁️ Mensagem personalizada removida."
        )

        return True

    except Exception as erro:

        print(
            f"❌ Erro removendo mensagem: {erro}"
        )

        return False


# =========================================================
# YOUTUBE
# =========================================================

def adicionar_youtube(
    guild_id,
    youtube_id,
    nome,
    uploads_playlist,
    ultimo_video
):

    try:

        dados = {
            "guild_id": guild_id,
            "youtube_id": youtube_id,
            "nome": nome,
            "uploads_playlist": uploads_playlist,
            "ultimo_video": ultimo_video,
            "ativo": True
        }

        resposta = (
            supabase
            .table("youtube_canais")
            .upsert(
                dados,
                on_conflict="guild_id,youtube_id"
            )
            .execute()
        )

        print(
            f"☁️ Canal do YouTube salvo: {nome}"
        )

        return resposta.data

    except Exception as erro:

        print(
            f"❌ Erro salvando canal do YouTube: {erro}"
        )

        return None


def remover_youtube(
    guild_id,
    youtube_id
):

    try:

        resposta = (
            supabase
            .table("youtube_canais")
            .delete()
            .eq("guild_id", guild_id)
            .eq("youtube_id", youtube_id)
            .execute()
        )

        removido = bool(resposta.data)

        if removido:

            print(
                f"☁️ Canal removido: {youtube_id}"
            )

        return removido

    except Exception as erro:

        print(
            f"❌ Erro removendo YouTube: {erro}"
        )

        return False


def listar_youtube(guild_id):

    try:

        resposta = (
            supabase
            .table("youtube_canais")
            .select(
                "youtube_id,nome,ultimo_video,ativo"
            )
            .eq("guild_id", guild_id)
            .order("nome")
            .execute()
        )

        resultados = []

        for canal in resposta.data:

            resultados.append((
                canal.get("youtube_id"),
                canal.get("nome"),
                canal.get("ultimo_video"),
                canal.get("ativo")
            ))

        return resultados

    except Exception as erro:

        print(
            f"❌ Erro listando canais: {erro}"
        )

        return []


def pegar_todos_youtube():

    try:

        resposta = (
            supabase
            .table("youtube_canais")
            .select(
                "id,guild_id,youtube_id,nome,"
                "uploads_playlist,ultimo_video,ativo"
            )
            .eq("ativo", True)
            .execute()
        )

        resultados = []

        for canal in resposta.data:

            resultados.append((
                canal.get("id"),
                canal.get("guild_id"),
                canal.get("youtube_id"),
                canal.get("nome"),
                canal.get("uploads_playlist"),
                canal.get("ultimo_video"),
                canal.get("ativo")
            ))

        return resultados

    except Exception as erro:

        print(
            f"❌ Erro buscando canais do YouTube: {erro}"
        )

        return []


def atualizar_ultimo_video(
    registro_id,
    video_id
):

    try:

        supabase.table("youtube_canais").update({
            "ultimo_video": video_id
        }).eq(
            "id",
            registro_id
        ).execute()

        print(
            f"☁️ Último vídeo atualizado: {video_id}"
        )

    except Exception as erro:

        print(
            f"❌ Erro atualizando último vídeo: {erro}"
        )

        # =========================================================
# CALL AUTO
# =========================================================

def configurar_call_auto(guild_id, channel_id):
    try:
        supabase.table("voice_auto_join").upsert({
            "guild_id": guild_id,
            "channel_id": channel_id,
            "enabled": True
        }).execute()

        print(
            f"☁️ CallAuto ativado no servidor {guild_id} "
            f"para o canal {channel_id}."
        )

        return True

    except Exception as erro:
        print(
            f"❌ Erro configurando CallAuto: {erro}"
        )

        return False


def desativar_call_auto(guild_id):
    try:
        supabase.table("voice_auto_join").update({
            "enabled": False
        }).eq(
            "guild_id",
            guild_id
        ).execute()

        print(
            f"☁️ CallAuto desativado no servidor {guild_id}."
        )

        return True

    except Exception as erro:
        print(
            f"❌ Erro desativando CallAuto: {erro}"
        )

        return False


def pegar_call_auto(guild_id):
    try:
        resposta = (
            supabase
            .table("voice_auto_join")
            .select("guild_id,channel_id,enabled")
            .eq("guild_id", guild_id)
            .execute()
        )

        if not resposta.data:
            return None

        dados = resposta.data[0]

        return (
            dados.get("guild_id"),
            dados.get("channel_id"),
            dados.get("enabled")
        )

    except Exception as erro:
        print(
            f"❌ Erro buscando configuração CallAuto: {erro}"
        )

        return None


def pegar_todos_call_auto():
    try:
        resposta = (
            supabase
            .table("voice_auto_join")
            .select("guild_id,channel_id,enabled")
            .eq("enabled", True)
            .execute()
        )

        resultados = []

        for dados in resposta.data:
            resultados.append((
                dados.get("guild_id"),
                dados.get("channel_id"),
                dados.get("enabled")
            ))

        return resultados

    except Exception as erro:
        print(
            f"❌ Erro buscando CallAuto: {erro}"
        )

        return []