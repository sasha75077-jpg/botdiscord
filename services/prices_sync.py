import asyncio
import os

from services.api_http import api_call

API_URL = os.getenv("PANEL_API_URL", "https://melancholia-api.sasha75077.workers.dev").rstrip("/")
SYNC_SECRET = os.getenv("PANEL_SYNC_SECRET", "")


def _api(method, path, payload=None):
    # gzip + маскировка UA + защита от обрыва живут в services/api_http.py
    return api_call(method, path, payload)


async def pull_prices() -> bool:
    """Подтянуть прайс с сайта в локальную БД. True если что-то изменилось."""
    if not SYNC_SECRET:
        return False
    try:
        data = await asyncio.to_thread(_api, "GET", "/prices")
    except Exception as e:
        print(f"[prices] warn pull: {e}")
        return False
    changed = False
    for item in (data or {}).get("prices", []) or []:
        key, price = item.get("item_key"), float(item.get("price") or 0)
        if not key:
            continue
        from database import fetch_one, execute
        row = await fetch_one("SELECT price FROM prices WHERE item_key = ?", (key,))
        if row is None:
            await execute("INSERT INTO prices(item_key, price) VALUES(?, ?)", (key, price))
            changed = True
        elif float(row["price"] or 0) != price:
            await execute("UPDATE prices SET price = ? WHERE item_key = ?", (price, key))
            changed = True
    # Локальные ключи, которых нет на сайте, - запушить на сайт
    try:
        from database import fetch_all, execute  # noqa
        local_rows = await fetch_all("SELECT item_key, price FROM prices", ())
        remote_keys = {i.get("item_key") for i in (data or {}).get("prices", []) or []}
        missing = {r["item_key"]: float(r["price"] or 0) for r in local_rows
                   if r["item_key"] not in remote_keys}
        if missing:
            await asyncio.to_thread(_api, "PUT", "/prices", {"items": missing})
    except Exception as e:
        print(f"[prices] warn push missing: {e}")
    return changed
