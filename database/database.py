import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE = BASE_DIR / "database.db"


def conectar():
    return sqlite3.connect(DATABASE)


def criar_banco():
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS servidores (
            id INTEGER PRIMARY KEY,
            canal_notificacao INTEGER,
            cargo_notificacao INTEGER,
            mensagem_youtube TEXT,
            youtube_ativo INTEGER DEFAULT 1,
            boas_vindas_ativo INTEGER DEFAULT 0,
            canal_boas_vindas INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS youtube_canais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            youtube_id TEXT NOT NULL,
            nome TEXT,
            uploads_playlist TEXT,
            ultimo_video TEXT,
            ativo INTEGER DEFAULT 1,
            UNIQUE(guild_id, youtube_id)
        )
    """)

    conexao.commit()
    conexao.close()


def criar_servidor(guild_id):
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO servidores (id)
        VALUES (?)
    """, (guild_id,))

    conexao.commit()
    conexao.close()


def pegar_servidor(guild_id):
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        SELECT *
        FROM servidores
        WHERE id = ?
    """, (guild_id,))

    resultado = cursor.fetchone()

    conexao.close()

    return resultado


def configurar_canal_notificacao(guild_id, canal_id):
    criar_servidor(guild_id)

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        UPDATE servidores
        SET canal_notificacao = ?
        WHERE id = ?
    """, (canal_id, guild_id))

    conexao.commit()
    conexao.close()


def configurar_cargo_notificacao(guild_id, cargo_id):
    criar_servidor(guild_id)

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        UPDATE servidores
        SET cargo_notificacao = ?
        WHERE id = ?
    """, (cargo_id, guild_id))

    conexao.commit()
    conexao.close()


def configurar_mensagem_youtube(guild_id, mensagem):
    criar_servidor(guild_id)

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        UPDATE servidores
        SET mensagem_youtube = ?
        WHERE id = ?
    """, (mensagem, guild_id))

    conexao.commit()
    conexao.close()


def adicionar_youtube(
    guild_id,
    youtube_id,
    nome,
    uploads_playlist,
    ultimo_video
):
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO youtube_canais
        (
            guild_id,
            youtube_id,
            nome,
            uploads_playlist,
            ultimo_video,
            ativo
        )
        VALUES (?, ?, ?, ?, ?, 1)
    """, (
        guild_id,
        youtube_id,
        nome,
        uploads_playlist,
        ultimo_video
    ))

    conexao.commit()
    conexao.close()


def remover_youtube(guild_id, youtube_id):
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        DELETE FROM youtube_canais
        WHERE guild_id = ?
        AND youtube_id = ?
    """, (guild_id, youtube_id))

    removido = cursor.rowcount > 0

    conexao.commit()
    conexao.close()

    return removido


def listar_youtube(guild_id):
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        SELECT
            youtube_id,
            nome,
            ultimo_video,
            ativo
        FROM youtube_canais
        WHERE guild_id = ?
        ORDER BY nome
    """, (guild_id,))

    resultados = cursor.fetchall()

    conexao.close()

    return resultados


def pegar_todos_youtube():
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        SELECT
            id,
            guild_id,
            youtube_id,
            nome,
            uploads_playlist,
            ultimo_video,
            ativo
        FROM youtube_canais
        WHERE ativo = 1
    """)

    resultados = cursor.fetchall()

    conexao.close()

    return resultados


def atualizar_ultimo_video(registro_id, video_id):
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        UPDATE youtube_canais
        SET ultimo_video = ?
        WHERE id = ?
    """, (video_id, registro_id))

    conexao.commit()
    conexao.close()