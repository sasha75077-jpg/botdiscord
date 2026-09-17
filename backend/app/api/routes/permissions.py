"""
API endpoints для управления ролями и правами доступа
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from pydantic import BaseModel, Field
from ...core.database import get_db, Database
from ..dependencies import get_current_user, require_admin, require_owner, require_role
import sys
import os

# Добавить путь к корневой папке для импорта database.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
from database import get_user_role, set_user_role, list_permissions, delete_permission

router = APIRouter(prefix="/api/guilds/{guild_id}/permissions", tags=["permissions"])


# ============================================================================
# Schemas
# ============================================================================

class PermissionResponse(BaseModel):
    discord_id: str
    role: str = Field(..., description="owner, admin, recruiter, user")
    granted_at: str
    granted_by: str | None

class PermissionListResponse(BaseModel):
    permissions: List[PermissionResponse]

class AssignRoleRequest(BaseModel):
    discord_id: str = Field(..., description="Discord ID пользователя")
    role: str = Field(..., description="owner, admin, recruiter, user")

class AssignRoleResponse(BaseModel):
    ok: bool
    message: str


# ============================================================================
# Endpoints
# ============================================================================

@router.get("", response_model=PermissionListResponse)
async def get_guild_permissions(
    guild_id: str,
    current_user: dict = Depends(require_role('admin')),
    db: Database = Depends(get_db)
):
    """
    Получить список всех пользователей с ролями на сервере.

    **Доступ:** Owner, Admin

    **Возвращает:**
    - Список пользователей с их ролями
    - Отсортировано по иерархии ролей (owner -> admin -> recruiter -> user)
    """

    # Admin может видеть только свой сервер
    if current_user["role"] == "admin" and current_user.get("guild_id") != guild_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен к этому серверу"
        )

    permissions = await list_permissions(guild_id)

    return PermissionListResponse(
        permissions=[
            PermissionResponse(
                discord_id=p["discord_id"],
                role=p["role"],
                granted_at=p["granted_at"],
                granted_by=p.get("granted_by")
            )
            for p in permissions
        ]
    )


@router.post("", response_model=AssignRoleResponse, status_code=status.HTTP_201_CREATED)
async def assign_role(
    guild_id: str,
    request: AssignRoleRequest,
    current_user: dict = Depends(require_role('admin')),
    db: Database = Depends(get_db)
):
    """
    Назначить роль пользователю.

    **Доступ:**
    - Owner: может назначить любую роль
    - Admin: может назначить только recruiter или user

    **Правила:**
    - Admin не может назначить роль owner
    - Admin не может назначить другого admin
    - Admin может работать только на своем сервере
    """

    # Проверить что admin работает со своим сервером
    if current_user["role"] == "admin" and current_user.get("guild_id") != guild_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен к этому серверу"
        )

    # Admin не может назначать owner или admin
    if current_user["role"] == "admin" and request.role in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin может назначить только роли recruiter или user"
        )

    # Проверить что роль валидна
    valid_roles = ["owner", "admin", "recruiter", "user"]
    if request.role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Невалидная роль. Допустимые: {', '.join(valid_roles)}"
        )

    # Назначить роль
    try:
        await set_user_role(
            guild_id=guild_id,
            discord_id=request.discord_id,
            role=request.role,
            granted_by=current_user.get("discord_id") or current_user.get("email")
        )

        return AssignRoleResponse(
            ok=True,
            message=f"Роль {request.role} назначена пользователю {request.discord_id}"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка назначения роли: {str(e)}"
        )


@router.delete("/{discord_id}", response_model=AssignRoleResponse)
async def remove_role(
    guild_id: str,
    discord_id: str,
    current_user: dict = Depends(require_role('admin')),
    db: Database = Depends(get_db)
):
    """
    Удалить роль пользователя на сервере.

    **Доступ:**
    - Owner: может удалить любую роль
    - Admin: может удалить только роли которые сам назначал (recruiter, user)

    **Правила:**
    - Admin не может удалить owner или admin
    - Admin может работать только на своем сервере
    - После удаления пользователь становится обычным user (по умолчанию)
    """

    # Проверить что admin работает со своим сервером
    if current_user["role"] == "admin" and current_user.get("guild_id") != guild_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен к этому серверу"
        )

    # Получить текущую роль пользователя
    target_user = await db.fetch_one(
        "SELECT role, granted_by FROM permissions WHERE guild_id = ? AND discord_id = ?",
        (guild_id, discord_id)
    )

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден или не имеет роли на этом сервере"
        )

    # Admin не может удалить owner или admin
    if current_user["role"] == "admin" and target_user["role"] in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin не может удалить роли owner или admin"
        )

    # Admin может удалить только те роли, которые сам назначал
    if current_user["role"] == "admin":
        current_discord_id = current_user.get("discord_id")
        if target_user.get("granted_by") != current_discord_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin может удалить только роли которые сам назначал"
            )

    # Удалить роль
    deleted = await delete_permission(guild_id, discord_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Роль не найдена"
        )

    return AssignRoleResponse(
        ok=True,
        message=f"Роль пользователя {discord_id} удалена. Теперь он обычный user."
    )


@router.get("/me", response_model=PermissionResponse)
async def get_my_role(
    guild_id: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Получить свою роль на сервере.

    **Доступ:** Любой авторизованный пользователь

    **Возвращает:**
    - Роль текущего пользователя на указанном сервере
    """

    discord_id = current_user.get("discord_id")

    if not discord_id:
        # Если это owner без Discord ID - вернуть owner
        if current_user["role"] == "owner":
            return PermissionResponse(
                discord_id="owner",
                role="owner",
                granted_at="",
                granted_by=None
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Discord ID не найден"
        )

    # Получить роль из БД
    permission = await db.fetch_one(
        "SELECT * FROM permissions WHERE guild_id = ? AND discord_id = ?",
        (guild_id, discord_id)
    )

    if not permission:
        # По умолчанию - user
        return PermissionResponse(
            discord_id=discord_id,
            role="user",
            granted_at="",
            granted_by=None
        )

    return PermissionResponse(
        discord_id=permission["discord_id"],
        role=permission["role"],
        granted_at=permission["granted_at"],
        granted_by=permission.get("granted_by")
    )
