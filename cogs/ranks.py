from database import fetch_one, execute

SYSTEM_MAIN = "main"
SYSTEM_ALT = "alt"


async def ensure_user(discord_id: str, guild_id: str):
    """Убедиться что пользователь существует в БД для данного сервера"""
    u = await fetch_one(
        "SELECT * FROM users WHERE guild_id = ? AND discord_id = ?",
        (guild_id, discord_id)
    )
    if not u:
        # Найти ранг "Freak" для этого сервера
        freak = await fetch_one(
            "SELECT rank_id FROM ranks WHERE guild_id = ? AND name = 'Freak' LIMIT 1",
            (guild_id,)
        )

        await execute(
            "INSERT INTO users(guild_id, discord_id, current_rank_id, family_total, tuning_total, surname_changed) "
            "VALUES (?, ?, ?, 0, 0, 0)",
            (guild_id, discord_id, freak["rank_id"] if freak else None),
        )
        u = await fetch_one(
            "SELECT * FROM users WHERE guild_id = ? AND discord_id = ?",
            (guild_id, discord_id)
        )
    return u


async def get_next_rank(guild_id: str, current_rank_id: int):
    """Получить следующий ранг для пользователя"""
    return await fetch_one(
        """
        SELECT r2.rank_id, r2.name, r2.role_id, r2.order_num
        FROM ranks r1
        JOIN ranks r2
          ON r2.guild_id = r1.guild_id AND r2.order_num > r1.order_num
        WHERE r1.guild_id = ? AND r1.rank_id = ?
        ORDER BY r2.order_num ASC
        LIMIT 1
        """,
        (guild_id, current_rank_id),
    )


async def get_main_req(guild_id: str, rank_from: int, rank_to: int):
    """Получить требования основной системы повышения"""
    return await fetch_one(
        "SELECT family_contracts FROM rank_requirements_main "
        "WHERE guild_id = ? AND rank_from = ? AND rank_to = ?",
        (guild_id, rank_from, rank_to),
    )


async def get_alt_req(guild_id: str, rank_from: int, rank_to: int):
    """Получить требования альтернативной системы повышения"""
    return await fetch_one(
        "SELECT family_contracts, tuning_contracts, require_surname_change "
        "FROM rank_requirements_alt WHERE guild_id = ? AND rank_from = ? AND rank_to = ?",
        (guild_id, rank_from, rank_to),
    )


async def promotion_status(discord_id: str, guild_id: str, system_type: str):
    """Проверить статус возможности повышения"""
    u = await ensure_user(discord_id, guild_id)
    cur_rank = await fetch_one(
        "SELECT * FROM ranks WHERE guild_id = ? AND rank_id = ?",
        (guild_id, u["current_rank_id"])
    )
    nxt = await get_next_rank(guild_id, u["current_rank_id"])

    if not nxt:
        return {"ok": False, "msg": "Ты уже на максимальном ранге.", "data": None}

    fam = int(u["family_total"] or 0)
    tun = int(u["tuning_total"] or 0)
    surname_changed = int(u["surname_changed"] or 0)

    if system_type == SYSTEM_MAIN:
        req = await get_main_req(guild_id, u["current_rank_id"], nxt["rank_id"])
        need_fam = int(req["family_contracts"]) if req else 0
        ok = fam >= need_fam
        return {
            "ok": ok,
            "msg": "",
            "data": {
                "system": SYSTEM_MAIN,
                "from": cur_rank["name"] if cur_rank else "?",
                "to": nxt["name"],
                "family_have": fam,
                "family_need": need_fam,
            },
        }

    if system_type == SYSTEM_ALT:
        req = await get_alt_req(guild_id, u["current_rank_id"], nxt["rank_id"])
        need_fam = int(req["family_contracts"]) if req else 0
        need_tun = int(req["tuning_contracts"]) if req else 0
        need_name = int(req["require_surname_change"]) if req else 0

        ok = (fam >= need_fam) and (tun >= need_tun) and ((not need_name) or surname_changed == 1)
        return {
            "ok": ok,
            "msg": "",
            "data": {
                "system": SYSTEM_ALT,
                "from": cur_rank["name"] if cur_rank else "?",
                "to": nxt["name"],
                "family_have": fam,
                "family_need": need_fam,
                "tuning_have": tun,
                "tuning_need": need_tun,
                "surname_required": bool(need_name),
                "surname_changed": bool(surname_changed),
            },
        }

    return {"ok": False, "msg": "Неизвестная система.", "data": None}


async def create_promo_report(discord_id: str, guild_id: str, system_type: str):
    """Создать отчет на повышение"""
    st = await promotion_status(discord_id, guild_id, system_type)
    if not st["data"]:
        return {"ok": False, "reason": st["msg"]}

    existing = await fetch_one(
        "SELECT report_id FROM promotion_reports "
        "WHERE guild_id = ? AND discord_id = ? AND system_type = ? AND status IN ('NEW','TAKEN') "
        "ORDER BY report_id DESC LIMIT 1",
        (guild_id, discord_id, system_type),
    )
    if existing:
        return {"ok": False, "reason": "У тебя уже есть отчёт на рассмотрении."}

    if not st["ok"]:
        return {"ok": False, "reason": "Недостаточно контрактов/условий для подачи."}

    u = await ensure_user(discord_id, guild_id)
    nxt = await get_next_rank(guild_id, u["current_rank_id"])
    if not nxt:
        return {"ok": False, "reason": "Следующий ранг не найден."}

    await execute(
        """
        INSERT INTO promotion_reports(guild_id, discord_id, from_rank_id, to_rank_id, system_type, submitted_at, status)
        VALUES (?, ?, ?, ?, ?, datetime('now'), 'NEW')
        """,
        (guild_id, discord_id, u["current_rank_id"], nxt["rank_id"], system_type),
    )
    rep = await fetch_one(
        "SELECT report_id FROM promotion_reports WHERE guild_id = ? AND discord_id = ? ORDER BY report_id DESC LIMIT 1",
        (guild_id, discord_id),
    )
    try:
        from services.api_sync import queue_promo_sync
        queue_promo_sync(str(guild_id), rep["report_id"], str(discord_id),
                         from_rank=u["current_rank_id"], to_rank=nxt["rank_id"], status="NEW")
    except Exception as e:
        print(f"[api_sync] warn: {e}")
    return {"ok": True, "report_id": rep["report_id"]}
