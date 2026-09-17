import asyncio
from database import fetch_one

async def main():
    r = await fetch_one("SELECT COUNT(*) AS cnt FROM ranks", ())
    print("ranks cnt =", r["cnt"])

asyncio.run(main())
