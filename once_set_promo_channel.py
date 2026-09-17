import asyncio
from database import init_db, execute

async def main():
    await init_db()
    await execute(
        "INSERT OR REPLACE INTO settings(key, value) VALUES('promotion_channel_id', ?)",
        ("1402587818185719878",)
    )
    print("Promotion channel set.")

if __name__ == "__main__":
    asyncio.run(main())