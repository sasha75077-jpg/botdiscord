# seed_ranks_v2.py
import asyncio
from database import init_db, execute, fetch_one

RANKS = [
    # name, role_id, min_contracts, sort_order
    ("Freak",    1323997283230154833, 0, 1),
    ("Newbie",   1323997629968814162, 0, 2),
    ("Main",     1323998363992985600, 0, 3),
    ("Verified", 1405605219869397053, 0, 4),
    ("Trusted",  1323998735327297586, 0, 5),
    ("Old",      1323998579144261712, 0, 6),
]

MAIN_REQ = [
    ("Freak", "Newbie", 5),
    ("Newbie", "Main", 15),
    ("Main", "Verified", 25),
    ("Verified", "Trusted", 35),
    ("Trusted", "Old", 50),
]

ALT_REQ = [
    ("Freak", "Newbie", 5, 0, 1),
    ("Newbie", "Main", 10, 3, 0),
    ("Main", "Verified", 15, 7, 0),
    ("Verified", "Trusted", 20, 12, 0),
    ("Trusted", "Old", 30, 20, 0),
]

async def get_rank_id(name: str):
    row = await fetch_one("SELECT id FROM ranks WHERE name=? LIMIT 1", (name,))
    return row["id"] if row else None

async def main():
    await init_db()

    # upsert by name
    for name, role_id, min_c, sort_o in RANKS:
        await execute(
            "UPDATE ranks SET role_id=?, min_contracts=?, sort_order=? WHERE name=?",
            (int(role_id), int(min_c), int(sort_o), name),
        )
        row = await fetch_one("SELECT id FROM ranks WHERE name=? LIMIT 1", (name,))
        if not row:
            await execute(
                "INSERT INTO ranks(name, role_id, min_contracts, sort_order) VALUES(?,?,?,?)",
                (name, int(role_id), int(min_c), int(sort_o)),
            )

    await execute("DELETE FROM rank_requirements_main", ())
    await execute("DELETE FROM rank_requirements_alt", ())

    for rf, rt, fam in MAIN_REQ:
        await execute(
            "INSERT INTO rank_requirements_main(rank_from, rank_to, family_contracts) VALUES(?,?,?)",
            (await get_rank_id(rf), await get_rank_id(rt), int(fam)),
        )

    for rf, rt, fam, tun, req_name in ALT_REQ:
        await execute(
            "INSERT INTO rank_requirements_alt(rank_from, rank_to, family_contracts, tuning_contracts, require_surname_change) VALUES(?,?,?,?,?)",
            (await get_rank_id(rf), await get_rank_id(rt), int(fam), int(tun), int(req_name)),
        )

    print("Seed v2 done.")

if __name__ == "__main__":
    asyncio.run(main())
