import asyncio
from database import init_db, execute

async def main():
    await init_db()
    await execute(
        "INSERT OR REPLACE INTO settings(key, value) VALUES('bonus_channel_id', ?)",
        ("1468075392819527720",)
    )
    print("Bonus channel set.")

if __name__ == "__main__":
    asyncio.run(main())
