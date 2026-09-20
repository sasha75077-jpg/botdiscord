import json
from database import fetch_one, fetch_all, execute, UniqueViolation
from utils.week import week_range_msk
import os
print("RUNNING bonus.py FROM:", os.path.abspath(__file__))

from services.prices import get_price


async def calc_bonus_for_user_week(discord_id: str, guild_id: str):
    """Рассчитать бонусы для пользователя за текущую неделю"""
    week_start, week_end = week_range_msk()

    rows = await fetch_all(
        """
        SELECT
          id,
          ts,
          contract_type,
          msk_date,
          msk_date_iso,
          calc_price,
          fish_type,
          fish_qty,
          ore_type,
          m_iron, m_silver, m_copper, m_tin, m_gold,
          goods_delivery, goods_loading,
          atelier_total_uniforms,
          marketplace_links_count,
          wn_category,
          wn_screenshots_count,
          tuning_has_screenshot
        FROM v_contract_value
        WHERE guild_id = ?
          AND discord_id = ?
          AND confirm_status = 'APPROVED'
          AND date(msk_date_iso) >= date(?)
          AND date(msk_date_iso) <= date(?)
        ORDER BY ts ASC
        """,
        (guild_id, discord_id, week_start, week_end)
    )

    total = 0.0
    items = []

    for c in rows:
        ct = c["contract_type"]
        amount = float(c["calc_price"] or 0.0)

        note = ""
        if ct == "активация":
            note = f"calc_price={amount}"
        elif ct == "дары-моря":
            note = f"fish={c['fish_type']} qty={c['fish_qty']} (manual)"
        elif ct == "агитации-wn":
            note = f"{str(c['wn_category'] or '')} | screenshots={int(c['wn_screenshots_count'] or 0)}"
        elif ct == "металлургия-сдача":
            note = str(c["ore_type"] or "")
        elif ct == "металлургия-добыча":
            note = (
                f"iron={int(c['m_iron'] or 0)}, "
                f"silver={int(c['m_silver'] or 0)}, "
                f"copper={int(c['m_copper'] or 0)}, "
                f"tin={int(c['m_tin'] or 0)}, "
                f"gold={int(c['m_gold'] or 0)}"
            )
        elif ct == "товары":
            note = f"delivery={c['goods_delivery']} loading={c['goods_loading']}"
        elif ct == "ателье":
            note = f"uniforms={int(c['atelier_total_uniforms'] or 0)}"
        elif ct == "агитации-маркетплейс":
            note = f"links={int(c['marketplace_links_count'] or 0)}"
        elif ct == "тюнинг":
            note = f"screenshot={c['tuning_has_screenshot']}"

        total += amount
        items.append({
            "contract_id": c["id"],
            "contract_type": ct,
            "amount": amount,
            "note": note,
            "msk_date": c["msk_date"],
        })

    return {
        "week_start": week_start,
        "week_end": week_end,
        "total": total,
        "items": items
    }


async def create_bonus_report(discord_id: str, guild_id: str):
    """Создать бонусный отчет для текущей недели"""
    week_start, week_end = week_range_msk()

    existing = await fetch_one(
        """
        SELECT report_id
        FROM bonus_reports
        WHERE guild_id = ?
          AND discord_id = ?
          AND week_start = ?
          AND week_end = ?
          AND status IN ('NEW','TAKEN','APPROVED')
        LIMIT 1
        """,
        (guild_id, discord_id, week_start, week_end)
    )
    if existing:
        return {"ok": False, "reason": "already_exists"}

    calc = await calc_bonus_for_user_week_range(discord_id, guild_id, week_start, week_end)

    if len(calc["items"]) == 0:
        return {"ok": False, "reason": "no_contracts"}

    try:
        await execute(
            """
            INSERT INTO bonus_reports(guild_id, discord_id, week_start, week_end, total_amount, contracts_json, submitted_at, status)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'), 'NEW')
            """,
            (guild_id, discord_id, week_start, week_end, float(calc["total"]), json.dumps(calc["items"], ensure_ascii=False))
        )
    except UniqueViolation as e:
        if "UNIQUE constraint failed" in str(e):
            return {"ok": False, "reason": "already_exists"}
        raise

    rep = await fetch_one(
        "SELECT report_id FROM bonus_reports WHERE guild_id = ? AND discord_id = ? ORDER BY report_id DESC LIMIT 1",
        (guild_id, discord_id)
    )
    try:
        from services.api_sync import queue_bonus_sync
        queue_bonus_sync(str(guild_id), rep["report_id"], str(discord_id),
                         amount=float(calc.get("total", 0)), status="NEW")
    except Exception as e:
        print(f"[api_sync] warn: {e}")
    return {"ok": True, "report_id": rep["report_id"], "calc": calc}


async def calc_bonus_for_user_week_range(discord_id: str, guild_id: str, week_start: str, week_end: str):
    """Рассчитать бонусы для пользователя за указанный период"""
    rows = await fetch_all(
        """
        SELECT
          id, ts, contract_type, msk_date_iso,
          calc_price,
          fish_type, fish_qty,
          ore_type,
          m_iron, m_silver, m_copper, m_tin, m_gold,
          goods_delivery, goods_loading,
          atelier_total_uniforms,
          marketplace_links_count,
          wn_category,
          wn_screenshots_count,
          tuning_has_screenshot
        FROM v_contract_value
        WHERE guild_id = ?
          AND discord_id = ?
          AND confirm_status = 'APPROVED'
          AND date(msk_date_iso) >= date(?)
          AND date(msk_date_iso) <= date(?)
        ORDER BY ts ASC
        """,
        (guild_id, discord_id, week_start, week_end)
    )

    total = 0.0
    items = []

    for c in rows:
        amount = float(c["calc_price"] or 0.0)
        total += amount

        ct = c["contract_type"]
        if ct == "дары-моря":
            note = f"fish={c['fish_type']} qty={c['fish_qty']} (manual)"
        elif ct == "агитации-wn":
            note = f"{str(c['wn_category'] or '')} | screenshots={int(c['wn_screenshots_count'] or 0)}"
        elif ct == "товары":
            note = f"delivery={c['goods_delivery']} loading={c['goods_loading']}"
        else:
            note = ""

        items.append({
            "contract_id": c["id"],
            "contract_type": ct,
            "amount": amount,
            "note": note,
            "msk_date_iso": c["msk_date_iso"],
        })

    return {"total": total, "items": items}


async def create_bonus_report_for_week(discord_id: str, guild_id: str, week_start: str, week_end: str):
    """Создать или обновить бонусный отчет за указанную неделю"""
    # Примечание: поле 'static' может не существовать в новой схеме
    # Если нужно, добавьте его в таблицу users или удалите эту проверку
    # u = await fetch_one("SELECT static FROM users WHERE guild_id = ? AND discord_id = ?", (guild_id, discord_id))
    # static_val = ((u["static"] or "").strip() if u else "")
    # if not static_val:
    #     return {"ok": False, "reason": "no_static"}

    calc = await calc_bonus_for_user_week_range(discord_id, guild_id, week_start, week_end)

    total = float(calc.get("total") or 0.0)
    if total <= 0:
        return {"ok": False, "reason": "no_contracts"}

    row = await fetch_one(
        """
        SELECT report_id, status
        FROM bonus_reports
        WHERE guild_id=? AND discord_id=? AND week_start=? AND week_end=?
        """,
        (guild_id, discord_id, week_start, week_end),
    )

    if row:
        st = (row["status"] or "").upper()
        rid = int(row["report_id"])

        if st == "REJECTED":
            await execute(
                """
                UPDATE bonus_reports
                SET status='DRAFT',
                    total_amount=?,
                    contracts_json=?,
                    submitted_at=datetime('now'),
                    taken_by=NULL,
                    reviewed_by=NULL,
                    reviewed_at=NULL,
                    decision=NULL,
                    reason=NULL
                WHERE report_id=?
                """,
                (total, json.dumps(calc["items"], ensure_ascii=False), rid),
            )
            try:
                from services.api_sync import queue_bonus_sync
                queue_bonus_sync(str(guild_id), rid, str(discord_id),
                                 amount=float(total), status="NEW")
            except Exception as e:
                print(f"[api_sync] warn: {e}")
            return {"ok": True, "report_id": rid, "calc": calc, "reopened": True}

        if st in ("DRAFT", "NEW"):
            await execute(
                """
                UPDATE bonus_reports
                SET total_amount=?,
                    contracts_json=?,
                    submitted_at=datetime('now')
                WHERE report_id=?
                """,
                (total, json.dumps(calc["items"], ensure_ascii=False), rid),
            )
            try:
                from services.api_sync import queue_bonus_sync
                queue_bonus_sync(str(guild_id), rid, str(discord_id),
                                 amount=float(total), status="NEW")
            except Exception as e:
                print(f"[api_sync] warn: {e}")
            return {"ok": True, "report_id": rid, "calc": calc, "updated": True, "status": st}

        return {"ok": False, "reason": "already_exists", "report_id": rid, "status": st}

    try:
        await execute(
            """
            INSERT INTO bonus_reports(
                guild_id, discord_id, week_start, week_end,
                total_amount, contracts_json,
                submitted_at, status
            )
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'), 'DRAFT')
            """,
            (
                guild_id, discord_id, week_start, week_end,
                total,
                json.dumps(calc["items"], ensure_ascii=False),
            ),
        )
    except UniqueViolation:
        return {"ok": False, "reason": "already_exists"}

    rep = await fetch_one(
        """
        SELECT report_id
        FROM bonus_reports
        WHERE guild_id=? AND discord_id=? AND week_start=? AND week_end=?
        """,
        (guild_id, discord_id, week_start, week_end),
    )
    try:
        from services.api_sync import queue_bonus_sync
        queue_bonus_sync(str(guild_id), rep["report_id"], str(discord_id),
                         amount=float(total), status="DRAFT")
    except Exception as e:
        print(f"[api_sync] warn: {e}")
    return {"ok": True, "report_id": rep["report_id"], "calc": calc, "reopened": False, "status": "DRAFT"}


async def delete_bonus_report(report_id: int, guild_id: str):
    """Удалить бонусный отчет"""
    row = await fetch_one(
        "SELECT report_id FROM bonus_reports WHERE guild_id = ? AND report_id = ?",
        (guild_id, report_id)
    )
    if not row:
        return {"ok": False, "reason": "not_found"}

    await execute("DELETE FROM bonus_reports WHERE guild_id = ? AND report_id = ?", (guild_id, report_id))
    return {"ok": True}
