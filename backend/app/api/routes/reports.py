from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from ...core.database import get_db, Database
from ...schemas import BonusReportDetail, BonusReportApprove
from ..dependencies import get_current_user, require_admin

router = APIRouter(prefix="/guilds/{guild_id}/reports", tags=["Reports"])

@router.get("/bonus")
async def list_bonus_reports(
    guild_id: str,
    status: Optional[str] = None,
    discord_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Список отчетов на бонусы"""

    # Проверить доступ
    if current_user["role"] not in ["owner", "admin"]:
        # Обычные пользователи видят только свои отчеты
        discord_id = current_user["discord_id"]

    if current_user["role"] != "owner" and current_user.get("guild_id") != guild_id:
        raise HTTPException(status_code=403, detail="Access denied")

    query = "SELECT * FROM bonus_reports WHERE guild_id = ?"
    params = [guild_id]

    if status:
        query += " AND status = ?"
        params.append(status)

    if discord_id:
        query += " AND discord_id = ?"
        params.append(discord_id)

    query += " ORDER BY submitted_at DESC"

    reports = await db.fetch_all(query, tuple(params))
    return reports

@router.get("/bonus/{report_id}")
async def get_bonus_report(
    guild_id: str,
    report_id: int,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Получить детали отчета на бонус"""

    report = await db.fetch_one(
        "SELECT * FROM bonus_reports WHERE report_id = ? AND guild_id = ?",
        (report_id, guild_id)
    )

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Проверить доступ
    if current_user["role"] not in ["owner", "admin"]:
        if report["discord_id"] != current_user["discord_id"]:
            raise HTTPException(status_code=403, detail="Access denied")

    return report

@router.put("/bonus/{report_id}/approve")
async def approve_bonus_report(
    guild_id: str,
    report_id: int,
    approval: BonusReportApprove,
    current_user: dict = Depends(require_admin),
    db: Database = Depends(get_db)
):
    """Одобрить или отклонить отчет на бонус"""

    # Проверить доступ
    if current_user["role"] != "owner" and current_user.get("guild_id") != guild_id:
        raise HTTPException(status_code=403, detail="Access denied")

    report = await db.fetch_one(
        "SELECT * FROM bonus_reports WHERE report_id = ? AND guild_id = ?",
        (report_id, guild_id)
    )

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Обновить статус
    await db.execute(
        """
        UPDATE bonus_reports SET
            status = ?,
            decision = ?,
            reason = ?,
            reviewed_by = ?,
            reviewed_at = CURRENT_TIMESTAMP
        WHERE report_id = ? AND guild_id = ?
        """,
        (
            approval.decision,
            approval.decision,
            approval.reason,
            current_user.get("discord_id") or current_user.get("email"),
            report_id,
            guild_id
        )
    )

    # Получить обновленный отчет
    updated_report = await db.fetch_one(
        "SELECT * FROM bonus_reports WHERE report_id = ? AND guild_id = ?",
        (report_id, guild_id)
    )

    # Отправить уведомление через WebSocket
    from ...main import manager
    await manager.broadcast(guild_id, {
        "type": "bonus_report_update",
        "report_id": report_id,
        "status": approval.decision
    })

    return updated_report

@router.get("/promotion")
async def list_promotion_reports(
    guild_id: str,
    status: Optional[str] = None,
    discord_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Список отчетов на повышение"""

    # Проверить доступ
    if current_user["role"] not in ["owner", "admin"]:
        discord_id = current_user["discord_id"]

    if current_user["role"] != "owner" and current_user.get("guild_id") != guild_id:
        raise HTTPException(status_code=403, detail="Access denied")

    query = """
        SELECT pr.*, rf.name as from_rank, rt.name as to_rank
        FROM promotion_reports pr
        LEFT JOIN ranks rf ON pr.from_rank_id = rf.rank_id
        LEFT JOIN ranks rt ON pr.to_rank_id = rt.rank_id
        WHERE pr.guild_id = ?
    """
    params = [guild_id]

    if status:
        query += " AND pr.status = ?"
        params.append(status)

    if discord_id:
        query += " AND pr.discord_id = ?"
        params.append(discord_id)

    query += " ORDER BY pr.submitted_at DESC"

    reports = await db.fetch_all(query, tuple(params))
    return reports
