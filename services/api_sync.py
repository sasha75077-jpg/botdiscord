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
# Cloudflare режет дефолтный Python-UA (1010) - маскируемся под браузер
BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def _headers():
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SYNC_SECRET}",
        "User-Agent": BROWSER_UA,
    }


def _post(path: str, payload: dict, method: str = "POST"):
    try:
        if not SYNC_SECRET:
            return
        req = urllib.request.Request(
            API_URL + path,
            data=json.dumps(payload).encode("utf-8"),
            headers=_headers(),
            method=method,
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            r.read()
    except Exception as e:
        print(f"[api_sync] warn: {e}")


def queue_sync(path: str, payload: dict, method: str = "POST"):
    """Общая постановка синка в очередь (не блокирует бота)."""
    if not SYNC_SECRET or not payload:
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(asyncio.to_thread(_post, path, payload, method))


def queue_contract_sync(guild_id, ts, discord_id, contract_type,
                        price=0, nickname=None, status="PENDING", static=None):
    """Поставить синхронизацию контракта в очередь (не блокирует бота)."""
    if not guild_id or not ts or not discord_id or not contract_type:
        return
    queue_sync(f"/guilds/{guild_id}/contracts/sync", {
        "ts": str(ts),
        "discord_id": str(discord_id),
        "contract_type": str(contract_type),
        "price": price or 0,
        "nickname": str(nickname) if nickname else None,
        "status": status or "PENDING",
        "static": str(static) if static else None,
    })


def queue_application_sync(guild_id, app_id, discord_id, status="PENDING", reason=None,
                           claimed_by=None, decided_by=None, thread_id=None,
                           log_channel_id=None, log_message_id=None, answers=None):
    """Синхронизация заявки (external_id = uuid бота)."""
    if not guild_id or not app_id or not discord_id:
        return
    queue_sync(f"/guilds/{guild_id}/applications/sync", {
        "external_id": str(app_id),
        "discord_id": str(discord_id),
        "status": status or "PENDING",
        "reason": reason,
        "claimed_by": str(claimed_by) if claimed_by else None,
        "decided_by": str(decided_by) if decided_by else None,
        "thread_id": str(thread_id) if thread_id else None,
        "log_channel_id": str(log_channel_id) if log_channel_id else None,
        "log_message_id": str(log_message_id) if log_message_id else None,
        "answers": answers or None,
    })


def queue_bonus_sync(guild_id, report_id, discord_id, amount=0, status="NEW", reason=None,
                     external_id=None):
    """Синхронизация премии. external_id по умолчанию = report_id бота;
    для строк-зеркал с сайта - 'site:<id>'."""
    if not guild_id or not report_id or not discord_id:
        return
    queue_sync(f"/guilds/{guild_id}/bonus-reports/sync", {
        "external_id": str(external_id) if external_id else str(report_id),
        "discord_id": str(discord_id),
        "amount": amount or 0,
        "status": status or "NEW",
        "reason": reason,
    })


def queue_promo_sync(guild_id, report_id, discord_id, from_rank=None, to_rank=None,
                     status="NEW", reason=None):
    """Синхронизация повышения (external_id = report_id бота)."""
    if not guild_id or not report_id or not discord_id:
        return
    queue_sync(f"/guilds/{guild_id}/promotion-reports/sync", {
        "external_id": str(report_id),
        "discord_id": str(discord_id),
        "from_rank": str(from_rank) if from_rank is not None else None,
        "to_rank": str(to_rank) if to_rank is not None else None,
        "status": status or "NEW",
        "reason": reason,
    })


def queue_app_message(guild_id, external_id, author_id, content):
    """Сообщение из Discord-треда в чат сайта."""
    if not guild_id or not external_id or not author_id or not (content or "").strip():
        return
    queue_sync(f"/guilds/{guild_id}/applications-messages/sync", {
        "external_id": str(external_id),
        "author_discord_id": str(author_id),
        "content": str(content)[:2000],
    })
