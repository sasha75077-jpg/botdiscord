from fastapi import APIRouter, Depends, HTTPException
from ...core.database import get_db, Database
from ...schemas import UserProfile, UserStats
from ..dependencies import get_current_user, require_admin

router = APIRouter(prefix="/guilds/{guild_id}/users", tags=["Users"])

@router.get("/me", response_model=UserProfile)
async def get_my_profile(
    guild_id: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Получить свой профиль"""

    discord_id = current_user.get("discord_id")
    if not discord_id:
        raise HTTPException(status_code=400, detail="Discord ID required")

    user = await db.fetch_one(
        """
        SELECT u.*, r.name as rank_name
        FROM users u
        LEFT JOIN ranks r ON u.current_rank_id = r.rank_id
        WHERE u.guild_id = ? AND u.discord_id = ?
        """,
        (guild_id, discord_id)
    )

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        **user,
        "username": f"User#{discord_id}",  # TODO: Получить из Discord API
        "avatar_url": None,
        "role": current_user["role"]
    }

@router.get("/{discord_id}")
async def get_user_profile(
    guild_id: str,
    discord_id: str,
    current_user: dict = Depends(require_admin),
    db: Database = Depends(get_db)
):
    """Получить профиль пользователя (Admin+)"""

    # Проверить доступ
    if current_user["role"] != "owner" and current_user.get("guild_id") != guild_id:
        raise HTTPException(status_code=403, detail="Access denied")

    user = await db.fetch_one(
        """
        SELECT u.*, r.name as rank_name
        FROM users u
        LEFT JOIN ranks r ON u.current_rank_id = r.rank_id
        WHERE u.guild_id = ? AND u.discord_id = ?
        """,
        (guild_id, discord_id)
    )

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Получить роль пользователя
    permission = await db.fetch_one(
        "SELECT role FROM permissions WHERE guild_id = ? AND discord_id = ?",
        (guild_id, discord_id)
    )

    return {
        **user,
        "username": f"User#{discord_id}",
        "avatar_url": None,
        "role": permission["role"] if permission else "user"
    }

@router.get("/{discord_id}/stats", response_model=UserStats)
async def get_user_stats(
    guild_id: str,
    discord_id: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Получить статистику пользователя"""

    # Пользователи могут видеть только свою статистику
    if current_user["role"] not in ["owner", "admin"]:
        if current_user.get("discord_id") != discord_id:
            raise HTTPException(status_code=403, detail="Access denied")

    # Проверить доступ к серверу
    if current_user["role"] != "owner" and current_user.get("guild_id") != guild_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Контракты
    total_contracts = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM contracts WHERE guild_id = ? AND discord_id = ?",
        (guild_id, discord_id)
    )

    pending_contracts = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM contracts WHERE guild_id = ? AND discord_id = ? AND confirm_status = 'PENDING'",
        (guild_id, discord_id)
    )

    approved_contracts = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM contracts WHERE guild_id = ? AND discord_id = ? AND confirm_status = 'APPROVED'",
        (guild_id, discord_id)
    )

    rejected_contracts = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM contracts WHERE guild_id = ? AND discord_id = ? AND confirm_status = 'REJECTED'",
        (guild_id, discord_id)
    )

    # Бонусы
    bonus_stats = await db.fetch_one(
        """
        SELECT
            COALESCE(SUM(total_amount), 0) as total_amount,
            COUNT(*) as approved_count
        FROM bonus_reports
        WHERE guild_id = ? AND discord_id = ? AND status = 'APPROVED'
        """,
        (guild_id, discord_id)
    )

    return UserStats(
        total_contracts=total_contracts["cnt"],
        pending_contracts=pending_contracts["cnt"],
        approved_contracts=approved_contracts["cnt"],
        rejected_contracts=rejected_contracts["cnt"],
        total_bonus_amount=bonus_stats["total_amount"],
        approved_bonus_reports=bonus_stats["approved_count"]
    )

@router.get("/")
async def list_users(
    guild_id: str,
    current_user: dict = Depends(require_admin),
    db: Database = Depends(get_db)
):
    """Список пользователей (Admin+)"""

    # Проверить доступ
    if current_user["role"] != "owner" and current_user.get("guild_id") != guild_id:
        raise HTTPException(status_code=403, detail="Access denied")

    users = await db.fetch_all(
        """
        SELECT u.*, r.name as rank_name
        FROM users u
        LEFT JOIN ranks r ON u.current_rank_id = r.rank_id
        WHERE u.guild_id = ?
        ORDER BY u.joined_at DESC
        """,
        (guild_id,)
    )

    return users
