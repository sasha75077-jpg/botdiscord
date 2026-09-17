from database import execute, fetch_one

async def delete_bonus_report(report_id: int):
    row = await fetch_one("SELECT report_id FROM bonus_reports WHERE report_id = ?", (report_id,))
    if not row:
        return {"ok": False, "reason": "not_found"}

    await execute("DELETE FROM bonus_reports WHERE report_id = ?", (report_id,))
    return {"ok": True}
