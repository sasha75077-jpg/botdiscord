from database import fetch_one, execute

async def get_setting(key: str) -> str | None:
    row = await fetch_one("SELECT value FROM settings WHERE key = ?", (key,))
    return str(row["value"]) if row and row["value"] is not None else None

async def set_setting(key: str, value: str):
    await execute("INSERT OR REPLACE INTO settings(key, value) VALUES(?,?)", (key, str(value)))
