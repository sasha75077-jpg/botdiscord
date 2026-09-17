from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from ..core.security import verify_token
from ..core.database import get_db, Database

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Database = Depends(get_db)
) -> dict:
    """Получить текущего пользователя из JWT токена"""
    token = credentials.credentials
    payload = verify_token(token, "access")

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    user_type = payload.get("user_type")

    if user_type == "owner":
        # Owner - проверяем в owner_account
        owner = await db.fetch_one(
            "SELECT * FROM owner_account WHERE id = 1"
        )
        if not owner:
            raise HTTPException(status_code=401, detail="Owner not found")

        return {
            "user_type": "owner",
            "email": owner["email"],
            "discord_id": owner.get("discord_id"),
            "role": "owner"
        }

    elif user_type == "discord":
        # Discord user - проверяем права
        discord_id = payload.get("discord_id")
        guild_id = payload.get("guild_id")

        if not discord_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        # Получить права пользователя
        permission = await db.fetch_one(
            "SELECT * FROM permissions WHERE discord_id = ? AND guild_id = ?",
            (discord_id, guild_id)
        )

        if not permission:
            # Если нет прав, считаем обычным пользователем
            role = "user"
        else:
            role = permission["role"]

        return {
            "user_type": "discord",
            "discord_id": discord_id,
            "guild_id": guild_id,
            "role": role
        }

    raise HTTPException(status_code=401, detail="Invalid user type")

async def require_owner(current_user: dict = Depends(get_current_user)):
    """Требовать права Owner"""
    if current_user["role"] != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner access required"
        )
    return current_user

async def require_admin(current_user: dict = Depends(get_current_user)):
    """Требовать права Admin или выше"""
    if current_user["role"] not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

async def require_recruiter(current_user: dict = Depends(get_current_user)):
    """Требовать права Recruiter или выше"""
    if current_user["role"] not in ["owner", "admin", "recruiter"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Recruiter access required"
        )
    return current_user

def require_role(min_role: str):
    """
    Динамическая проверка минимальной роли.

    Args:
        min_role: Минимальная требуемая роль ('owner', 'admin', 'recruiter', 'user')

    Returns:
        Dependency функция для FastAPI

    Example:
        @router.get("/some-endpoint", dependencies=[Depends(require_role('admin'))])
    """
    role_hierarchy = {
        'owner': 4,
        'admin': 3,
        'recruiter': 2,
        'user': 1
    }

    min_level = role_hierarchy.get(min_role, 0)

    async def _check_role(current_user: dict = Depends(get_current_user)):
        user_level = role_hierarchy.get(current_user["role"], 0)

        if user_level < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Требуется роль {min_role} или выше"
            )

        return current_user

    return _check_role

async def get_guild_from_user(
    guild_id: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> dict:
    """Проверить доступ пользователя к серверу"""

    # Owner имеет доступ ко всем серверам
    if current_user["role"] == "owner":
        guild = await db.fetch_one(
            "SELECT * FROM guilds WHERE guild_id = ?",
            (guild_id,)
        )
        if not guild:
            raise HTTPException(status_code=404, detail="Guild not found")
        return guild

    # Другие пользователи только к своему серверу
    if current_user.get("guild_id") != guild_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this guild denied"
        )

    guild = await db.fetch_one(
        "SELECT * FROM guilds WHERE guild_id = ?",
        (guild_id,)
    )

    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")

    return guild
