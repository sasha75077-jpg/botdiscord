import asyncio
from database import init_db, execute, fetch_one

RANKS = [
    ("Freak", 1, None),
    ("Newbie", 2, None),
    ("Main", 3, None),
    ("Verified", 4, None),
    ("Trusted", 5, None),
    ("Old", 6, None),
]

# Основная: family-only
MAIN_REQ = [
    ("Freak", "Newbie", 5),
    ("Newbie", "Main", 15),
    ("Main", "Verified", 25),
    ("Verified", "Trusted", 35),
    ("Trusted", "Old", 50),
]

# Альтернатива: family + tuning + условие фамилии на первом шаге
ALT_REQ = [
    ("Freak", "Newbie", 5, 0, 1),   # require surname change
    ("Newbie", "Main", 10, 3, 0),
    ("Main", "Verified", 15, 7, 0),
    ("Verified", "Trusted", 20, 12, 0),
    ("Trusted", "Old", 30, 20, 0),
]

async def get_rank_id(name: str):
    row = await fetch_one("SELECT id FROM ranks WHERE name = ?", (name,))
    return row["rank_id"] if row else None

async def main():
    await init_db()

    for name, order_num, role_id in RANKS:
        await execute(
            "INSERT OR IGNORE INTO ranks(name, order_num, role_id) VALUES (?, ?, ?)",
            (name, order_num, role_id)
        )

    for rf, rt, fam in MAIN_REQ:
        rf_id = await get_rank_id(rf)
        rt_id = await get_rank_id(rt)
        await execute(
            "INSERT OR REPLACE INTO rank_requirements_main(rank_from, rank_to, family_contracts) VALUES (?, ?, ?)",
            (rf_id, rt_id, fam)
        )

    for rf, rt, fam, tun, req_name in ALT_REQ:
        rf_id = await get_rank_id(rf)
        rt_id = await get_rank_id(rt)
        await execute(
            """INSERT OR REPLACE INTO rank_requirements_alt
               (rank_from, rank_to, family_contracts, tuning_contracts, require_surname_change)
               VALUES (?, ?, ?, ?, ?)""",
            (rf_id, rt_id, fam, tun, req_name)
        )

    print("Seed done.")

if __name__ == "__main__":
    asyncio.run(main())
