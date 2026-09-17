from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from ...core.database import get_db, Database
from ...schemas import GuildDetail, GuildSettings, GuildModules
from ..dependencies import get_current_user, require_owner, require_admin

router = APIRouter(prefix="/guilds", tags=["Guilds"])

@router.get("/", dependencies=[Depends(require_owner)])
async def list_guilds(
    is_active: Optional[bool] = None,
    db: Database = Depends(get_db)
):
    """Список всех серверов (только для Owner)"""
    query = "SELECT * FROM guilds"
    params = ()

    if is_active is not None:
        query += " WHERE is_active = ?"
        params = (is_active,)

    guilds = await db.fetch_all(query, params)

    # Добавить статистику для каждого сервера
    result = []
    for guild in guilds:
        guild_id = guild["guild_id"]

        # Подсчитать пользователей
        users_count = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM users WHERE guild_id = ?",
            (guild_id,)
        )

        # Подсчитать контракты
        contracts_count = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM contracts WHERE guild_id = ?",
            (guild_id,)
        )

        pending_count = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM contracts WHERE guild_id = ? AND confirm_status = 'PENDING'",
            (guild_id,)
        )

        result.append({
            **guild,
            "total_users": users_count["cnt"],
            "total_contracts": contracts_count["cnt"],
            "pending_contracts": pending_count["cnt"]
        })

    return result

@router.get("/{guild_id}")
async def get_guild(
    guild_id: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Получить информацию о сервере"""

    # Owner может видеть все серверы
    if current_user["role"] != "owner":
        # Проверить что это сервер пользователя
        if current_user.get("guild_id") != guild_id:
            raise HTTPException(status_code=403, detail="Access denied")

    guild = await db.fetch_one(
        "SELECT * FROM guilds WHERE guild_id = ?",
        (guild_id,)
    )

    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")

    # Статистика
    users_count = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM users WHERE guild_id = ?",
        (guild_id,)
    )
    contracts_count = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM contracts WHERE guild_id = ?",
        (guild_id,)
    )
    pending_count = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM contracts WHERE guild_id = ? AND confirm_status = 'PENDING'",
        (guild_id,)
    )

    return {
        **guild,
        "total_users": users_count["cnt"],
        "total_contracts": contracts_count["cnt"],
        "pending_contracts": pending_count["cnt"]
    }

@router.get("/{guild_id}/settings")
async def get_guild_settings(
    guild_id: str,
    current_user: dict = Depends(require_admin),
    db: Database = Depends(get_db)
):
    """Получить настройки сервера"""

    # Проверить доступ
    if current_user["role"] != "owner" and current_user.get("guild_id") != guild_id:
        raise HTTPException(status_code=403, detail="Access denied")

    settings = await db.fetch_all(
        "SELECT setting_key, setting_value FROM guild_settings WHERE guild_id = ?",
        (guild_id,)
    )

    return {
        "guild_id": guild_id,
        "settings": {s["setting_key"]: s["setting_value"] for s in settings}
    }

@router.put("/{guild_id}/settings")
async def update_guild_settings(
    guild_id: str,
    settings: GuildSettings,
    current_user: dict = Depends(require_admin),
    db: Database = Depends(get_db)
):
    """Обновить настройки сервера"""

    # Проверить доступ
    if current_user["role"] != "owner" and current_user.get("guild_id") != guild_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Обновить каждую настройку
    for key, value in settings.settings.items():
        await db.execute(
            """
            INSERT INTO guild_settings (guild_id, setting_key, setting_value, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(guild_id, setting_key) DO UPDATE SET
                setting_value = excluded.setting_value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (guild_id, key, value)
        )

    return {"message": "Settings updated"}

@router.get("/{guild_id}/modules")
async def get_guild_modules(
    guild_id: str,
    current_user: dict = Depends(require_admin),
    db: Database = Depends(get_db)
):
    """Получить модули сервера"""

    # Проверить доступ
    if current_user["role"] != "owner" and current_user.get("guild_id") != guild_id:
        raise HTTPException(status_code=403, detail="Access denied")

    modules = await db.fetch_all(
        "SELECT * FROM guild_modules WHERE guild_id = ?",
        (guild_id,)
    )

    return {"guild_id": guild_id, "modules": modules}

@router.put("/{guild_id}/modules/{module_name}")
async def toggle_guild_module(
    guild_id: str,
    module_name: str,
    is_enabled: bool,
    current_user: dict = Depends(require_admin),
    db: Database = Depends(get_db)
):
    """Включить/выключить модуль"""

    # Проверить доступ
    if current_user["role"] != "owner" and current_user.get("guild_id") != guild_id:
        raise HTTPException(status_code=403, detail="Access denied")

    await db.execute(
        """
        INSERT INTO guild_modules (guild_id, module_name, is_enabled)
        VALUES (?, ?, ?)
        ON CONFLICT(guild_id, module_name) DO UPDATE SET
            is_enabled = excluded.is_enabled
        """,
        (guild_id, module_name, is_enabled)
    )

    # Отправить уведомление через WebSocket
    from ...main import manager
    await manager.broadcast(guild_id, {
        "type": "module_update",
        "module": module_name,
        "is_enabled": is_enabled
    })

    return {"message": f"Module {module_name} {'enabled' if is_enabled else 'disabled'}"}
