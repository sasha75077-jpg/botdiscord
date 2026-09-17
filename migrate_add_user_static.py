import asyncio
import aiosqlite
from config import DB_PATH

async def main():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("PRAGMA table_info(users)")
        cols = [row[1] for row in await cur.fetchall()]
        if "static" not in cols:
            await db.execute("ALTER TABLE users ADD COLUMN static TEXT")
            await db.commit()
            print("Added users.static")
        else:
            print("users.static already exists")

asyncio.run(main())
