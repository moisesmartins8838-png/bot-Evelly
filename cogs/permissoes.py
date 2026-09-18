import os
import discord


def is_owner(user: discord.abc.User) -> bool:
    """Verifica se o usuário é o proprietário da Evelly."""
    try:
        owner_id = int(os.getenv("OWNER_ID", "0"))
    except ValueError:
        owner_id = 0

    return user.id == owner_id


def is_admin(user: discord.abc.User) -> bool:
    """Verifica se o usuário possui a permissão Administrador no Discord."""
    if not isinstance(user, discord.Member):
        return False

    return user.guild_permissions.administrator


def pode_controlar_evelly(user: discord.abc.User) -> bool:
    """
    Permite controlar a Evelly quando:
    - o usuário é o proprietário definido no OWNER_ID; ou
    - o usuário possui Administrador no Discord.
    """
    return is_owner(user) or is_admin(user)


def nivel_permissao(user: discord.abc.User) -> str:
    """Retorna o nível de permissão do usuário."""
    if is_owner(user):
        return "OWNER"

    if is_admin(user):
        return "ADMIN"

    return "USER"