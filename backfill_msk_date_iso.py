import asyncio
import aiosqlite
from config import DB_PATH

def to_iso(ddmmyyyy: str) -> str | None:
    if not ddmmyyyy:
        return None
    s = str(ddmmyyyy).strip()
    # ожидаем "dd-MM-yyyy"
    parts = s.split("-")
    if len(parts) != 3:
        return None
    dd, mm, yyyy = parts
    if len(yyyy) != 4:
        return None
    return f"{yyyy.zfill(4)}-{mm.zfill(2)}-{dd.zfill(2)}"

async def main():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await db.execute_fetchall(
            "SELECT id, msk_date FROM contracts WHERE msk_date_iso IS NULL OR msk_date_iso = ''"
        )
        updated = 0
        for r in rows:
            iso = to_iso(r["msk_date"])
            if iso:
                await db.execute(
                    "UPDATE contracts SET msk_date_iso = ? WHERE id = ?",
                    (iso, r["id"])
                )
                updated += 1
        await db.commit()
        print("Backfilled:", updated)

asyncio.run(main())
