from datetime import datetime, timezone
from database.database import supabase


def _now():
    return datetime.now(timezone.utc).isoformat()


def adicionar_canal(guild_id, youtube_id, nome, uploads_playlist, ultimo_video):
    try:
        data = {
            "guild_id": guild_id,
            "youtube_id": youtube_id,
            "nome": nome,
            "uploads_playlist": uploads_playlist,
            "ultimo_video": ultimo_video,
            "ativo": True,
        }
        response = supabase.table("youtube_canais").upsert(
            data, on_conflict="guild_id,youtube_id"
        ).execute()
        return bool(response.data)
    except Exception as e:
        print(f"❌ YouTube DB adicionar: {e}", flush=True)
        return False


def remover_canal(guild_id, youtube_id):
    try:
        response = (
            supabase.table("youtube_canais")
            .delete()
            .eq("guild_id", guild_id)
            .eq("youtube_id", youtube_id)
            .execute()
        )
        return bool(response.data)
    except Exception as e:
        print(f"❌ YouTube DB remover: {e}", flush=True)
        return False


def listar_canais(guild_id):
    try:
        response = (
            supabase.table("youtube_canais")
            .select("id,guild_id,youtube_id,nome,uploads_playlist,ultimo_video,ativo")
            .eq("guild_id", guild_id)
            .order("nome")
            .execute()
        )
        return response.data or []
    except Exception as e:
        print(f"❌ YouTube DB listar: {e}", flush=True)
        return []


def pegar_todos_canais():
    try:
        response = (
            supabase.table("youtube_canais")
            .select("id,guild_id,youtube_id,nome,uploads_playlist,ultimo_video,ativo")
            .eq("ativo", True)
            .execute()
        )
        return response.data or []
    except Exception as e:
        print(f"❌ YouTube DB todos: {e}", flush=True)
        return []


def atualizar_ultimo_video(record_id, video_id):
    try:
        supabase.table("youtube_canais").update(
            {"ultimo_video": video_id}
        ).eq("id", record_id).execute()
        return True
    except Exception as e:
        print(f"❌ YouTube DB último vídeo: {e}", flush=True)
        return False


def atualizar_uploads_playlist(record_id, playlist_id):
    try:
        supabase.table("youtube_canais").update(
            {"uploads_playlist": playlist_id}
        ).eq("id", record_id).execute()
        return True
    except Exception as e:
        print(f"❌ YouTube DB playlist: {e}", flush=True)
        return False


def pegar_config(guild_id):
    try:
        response = (
            supabase.table("youtube_config")
            .select("*")
            .eq("guild_id", guild_id)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"❌ YouTube DB config: {e}", flush=True)
        return None


def salvar_config(guild_id, **fields):
    try:
        fields["guild_id"] = guild_id
        fields["updated_at"] = _now()
        supabase.table("youtube_config").upsert(
            fields, on_conflict="guild_id"
        ).execute()
        return True
    except Exception as e:
        print(f"❌ YouTube DB salvar config: {e}", flush=True)
        return False


def salvar_live(guild_id, youtube_id, video_id, titulo, started_at, notified=True):
    try:
        data = {
            "guild_id": guild_id,
            "youtube_id": youtube_id,
            "video_id": video_id,
            "titulo": titulo,
            "started_at": started_at or _now(),
            "notified": notified,
            "ended_at": None,
        }
        supabase.table("youtube_lives").upsert(
            data, on_conflict="guild_id,youtube_id,video_id"
        ).execute()
        return True
    except Exception as e:
        print(f"❌ YouTube DB live: {e}", flush=True)
        return False


def live_ja_notificada(guild_id, youtube_id, video_id):
    try:
        response = (
            supabase.table("youtube_lives")
            .select("id")
            .eq("guild_id", guild_id)
            .eq("youtube_id", youtube_id)
            .eq("video_id", video_id)
            .eq("notified", True)
            .is_("ended_at", "null")
            .limit(1)
            .execute()
        )
        return bool(response.data)
    except Exception as e:
        print(f"❌ YouTube DB live check: {e}", flush=True)
        return False


def finalizar_live(guild_id, youtube_id):
    try:
        supabase.table("youtube_lives").update(
            {"ended_at": _now()}
        ).eq("guild_id", guild_id).eq(
            "youtube_id", youtube_id
        ).is_("ended_at", "null").execute()
        return True
    except Exception as e:
        print(f"❌ YouTube DB live finalização: {e}", flush=True)
        return False
