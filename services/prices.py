from database import fetch_one, fetch_all, execute

async def get_price(key: str) -> float:
    row = await fetch_one("SELECT price FROM prices WHERE item_key = ?", (key,))
    return float(row["price"]) if row else 0.0

async def get_prices_where(where_sql: str):
    return await fetch_all(
        f"SELECT item_key, price FROM prices WHERE {where_sql} ORDER BY item_key ASC",
        ()
    )

async def set_price_db(item_key: str, price: float):
    await execute(
        "INSERT INTO prices(item_key, price) VALUES(?, ?) "
        "ON CONFLICT(item_key) DO UPDATE SET price=excluded.price",
        (item_key, float(price))
    )

