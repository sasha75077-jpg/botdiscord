from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from ...core.database import get_db, Database
from ...schemas import ContractDetail, ContractUpdate, ContractListResponse
from ..dependencies import get_current_user, require_admin

router = APIRouter(prefix="/guilds/{guild_id}/contracts", tags=["Contracts"])

@router.get("/", response_model=ContractListResponse)
async def list_contracts(
    guild_id: str,
    status: Optional[str] = None,
    discord_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Список контрактов"""

    # Проверить доступ
    if current_user["role"] not in ["owner", "admin"]:
        # Обычные пользователи видят только свои контракты
        discord_id = current_user["discord_id"]

    if current_user["role"] != "owner" and current_user.get("guild_id") != guild_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Построить запрос
    query = "SELECT * FROM contracts WHERE guild_id = ?"
    params = [guild_id]

    if status:
        query += " AND confirm_status = ?"
        params.append(status)

    if discord_id:
        query += " AND discord_id = ?"
        params.append(discord_id)

    # Подсчитать общее количество
    count_query = query.replace("SELECT *", "SELECT COUNT(*) as cnt")
    total_result = await db.fetch_one(count_query, tuple(params))
    total = total_result["cnt"]

    # Добавить пагинацию
    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.append(page_size)
    params.append((page - 1) * page_size)

    contracts = await db.fetch_all(query, tuple(params))

    return ContractListResponse(
        contracts=contracts,
        total=total,
        page=page,
        page_size=page_size
    )

@router.get("/{contract_id}")
async def get_contract(
    guild_id: str,
    contract_id: int,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Получить детали контракта"""

    contract = await db.fetch_one(
        "SELECT * FROM contracts WHERE id = ? AND guild_id = ?",
        (contract_id, guild_id)
    )

    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    # Проверить доступ
    if current_user["role"] not in ["owner", "admin"]:
        # Пользователи могут видеть только свои контракты
        if contract["discord_id"] != current_user["discord_id"]:
            raise HTTPException(status_code=403, detail="Access denied")

    return contract

@router.put("/{contract_id}")
async def update_contract(
    guild_id: str,
    contract_id: int,
    update: ContractUpdate,
    current_user: dict = Depends(require_admin),
    db: Database = Depends(get_db)
):
    """Обновить контракт (одобрение/отклонение)"""

    # Проверить доступ
    if current_user["role"] != "owner" and current_user.get("guild_id") != guild_id:
        raise HTTPException(status_code=403, detail="Access denied")

    contract = await db.fetch_one(
        "SELECT * FROM contracts WHERE id = ? AND guild_id = ?",
        (contract_id, guild_id)
    )

    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    # Обновить статус
    fields = []
    params = []

    if update.confirm_status:
        fields.append("confirm_status = ?")
        params.append(update.confirm_status)
        fields.append("confirmed_by = ?")
        params.append(current_user.get("discord_id") or current_user.get("email"))
        fields.append("confirmed_at = ?")
        params.append("CURRENT_TIMESTAMP")

    if update.reject_reason:
        fields.append("reject_reason = ?")
        params.append(update.reject_reason)

    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    query = f"UPDATE contracts SET {', '.join(fields)} WHERE id = ? AND guild_id = ?"
    params.extend([contract_id, guild_id])

    await db.execute(query, tuple(params))

    # Получить обновленный контракт
    updated_contract = await db.fetch_one(
        "SELECT * FROM contracts WHERE id = ? AND guild_id = ?",
        (contract_id, guild_id)
    )

    # Отправить уведомление через WebSocket
    from ...main import manager
    await manager.broadcast(guild_id, {
        "type": "contract_update",
        "contract_id": contract_id,
        "status": update.confirm_status
    })

    return updated_contract

@router.delete("/{contract_id}")
async def delete_contract(
    guild_id: str,
    contract_id: int,
    current_user: dict = Depends(require_admin),
    db: Database = Depends(get_db)
):
    """Удалить контракт"""

    # Проверить доступ
    if current_user["role"] != "owner" and current_user.get("guild_id") != guild_id:
        raise HTTPException(status_code=403, detail="Access denied")

    contract = await db.fetch_one(
        "SELECT * FROM contracts WHERE id = ? AND guild_id = ?",
        (contract_id, guild_id)
    )

    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    await db.execute(
        "DELETE FROM contracts WHERE id = ? AND guild_id = ?",
        (contract_id, guild_id)
    )

    # Отправить уведомление через WebSocket
    from ...main import manager
    await manager.broadcast(guild_id, {
        "type": "contract_delete",
        "contract_id": contract_id
    })

    return {"message": "Contract deleted"}

@router.get("/stats")
async def get_contracts_stats(
    guild_id: str,
    current_user: dict = Depends(require_admin),
    db: Database = Depends(get_db)
):
    """Статистика контрактов"""

    # Проверить доступ
    if current_user["role"] != "owner" and current_user.get("guild_id") != guild_id:
        raise HTTPException(status_code=403, detail="Access denied")

    stats = {}

    # Общее количество
    total = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM contracts WHERE guild_id = ?",
        (guild_id,)
    )
    stats["total"] = total["cnt"]

    # По статусам
    by_status = await db.fetch_all(
        "SELECT confirm_status, COUNT(*) as cnt FROM contracts WHERE guild_id = ? GROUP BY confirm_status",
        (guild_id,)
    )
    stats["by_status"] = {row["confirm_status"]: row["cnt"] for row in by_status}

    # По типам
    by_type = await db.fetch_all(
        "SELECT contract_type, COUNT(*) as cnt FROM contracts WHERE guild_id = ? GROUP BY contract_type",
        (guild_id,)
    )
    stats["by_type"] = {row["contract_type"]: row["cnt"] for row in by_type}

    return stats
