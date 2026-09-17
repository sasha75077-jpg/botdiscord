import asyncio
from database import init_db, execute, fetch_all

ROLE_IDS = {
    "Freak":    "1323997283230154833",
    "Newbie":   "1323997629968814162",
    "Main":     "1323998363992985600",
    "Verified": "1405605219869397053",
    "Trusted":  "1323998735327297586",
    "Old":      "1323998579144261712",
}

async def main():
    await init_db()
    rows = await fetch_all("SELECT id, name FROM ranks", ())
    for r in rows:
        role_id = ROLE_IDS.get(r["name"])
        if role_id:
            await execute("UPDATE ranks SET role_id = ? WHERE id = ?", (role_id, r["rank_id"]))
    print("Rank roles updated.")

if __name__ == "__main__":
    asyncio.run(main())
