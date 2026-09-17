import asyncio
import aiosqlite
from config import DB_PATH

async def main():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("PRAGMA table_info(contracts)")
        cols = [row[1] for row in await cur.fetchall()]  # row[1] = name
        if "msk_date_iso" not in cols:
            await db.execute("ALTER TABLE contracts ADD COLUMN msk_date_iso TEXT")
            await db.commit()
            print("Added contracts.msk_date_iso")
        else:
            print("contracts.msk_date_iso already exists")

asyncio.run(main())
