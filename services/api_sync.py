"""Синхронизация контрактов из локальной bot.db в облачную панель (Cloudflare D1).

Работает fire-and-forget: ошибки сети логируются и НЕ роняют бота.
Отключается пустым PANEL_SYNC_SECRET в .env.
"""
import asyncio
import json
import os
import urllib.request

API_URL = os.getenv("PANEL_API_URL", "https://melancholia-api.sasha75077.workers.dev").rstrip("/")
SYNC_SECRET = os.getenv("PANEL_SYNC_SECRET", "")


def _post(path: str, payload: dict):
    try:
        if not SYNC_SECRET:
            return
        req = urllib.request.Request(
            API_URL + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {SYNC_SECRET}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            r.read()
    except Exception as e:
        print(f"[api_sync] warn: {e}")


def queue_contract_sync(guild_id, ts, discord_id, contract_type,
                        price=0, nickname=None, status="PENDING"):
    """Поставить синхронизацию контракта в очередь (не блокирует бота)."""
    if not SYNC_SECRET or not guild_id or not ts or not discord_id or not contract_type:
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    payload = {
        "ts": str(ts),
        "discord_id": str(discord_id),
        "contract_type": str(contract_type),
        "price": price or 0,
        "nickname": str(nickname) if nickname else None,
        "status": status or "PENDING",
    }
    loop.create_task(asyncio.to_thread(_post, f"/guilds/{guild_id}/contracts/sync", payload))
