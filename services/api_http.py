"""Единая точка HTTP-доступа бота к API панели.

Почему отдельный модуль и почему обязателен gzip
-------------------------------------------------
Линия до workers.dev из РФ режет большой поток байтов (contracts?limit=500
отдает ~191 КБ и ползет со ~280 Б/с -> вечный таймаут). Тот же ответ под
gzip весит ~10 КБ и доходит за ~1 с. Поэтому сюда всегда шлется
Accept-Encoding, а ответ распаковывается вручную: urllib этого не делает.

Также здесь живет маскировка User-Agent: Cloudflare отдает 1010 на
дефолтном Python-заголовке, поэтому всегда ставим браузерный UA.
"""
import gzip
import json
import os
import time
import urllib.error
import urllib.request

API_URL = os.getenv("PANEL_API_URL", "https://melancholia-api.sasha75077.workers.dev").rstrip("/")
SYNC_SECRET = os.getenv("PANEL_SYNC_SECRET", "")
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
# Гzip спасает большой payload, deflate почти ничего не весит, но бесплатен
ACCEPT_ENCODING = "gzip, deflate"

# GET/DELETE идемпотентны - их можно повторить на новом соединении.
# POST трогать нельзя: повтор может продублировать эффект на сервере.
RETRY_METHODS = {"GET", "DELETE"}


def _build(path, payload, method, secret, extra_headers):
    headers = {
        "User-Agent": BROWSER_UA,
        "Accept-Encoding": ACCEPT_ENCODING,
    }
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if secret is not None:
        headers["Authorization"] = f"Bearer {secret}"
    if extra_headers:
        headers.update(extra_headers)
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    return urllib.request.Request(API_URL + path, data=data, headers=headers, method=method)


def _read(resp):
    raw = resp.read()
    if (resp.headers.get("Content-Encoding") or "").lower() == "gzip":
        raw = gzip.decompress(raw)
    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        return None
    return json.loads(text)


def api_call(method, path, payload=None, timeout=20, secret=None, retries=1):
    """Вызов API панели. Возвращает распакованный JSON (или None на пустом теле).

    secret=None -> берется PANEL_SYNC_SECRET из окружения. Пустой секрет
    означает "синк отключен", и вызов возвращает None, не ходя в сеть.
    """
    if secret is None:
        secret = SYNC_SECRET
        if not secret:
            return None
    req = _build(path, payload, method, secret, None)
    last = None
    retryable = method.upper() in RETRY_METHODS
    attempts = (retries + 1) if retryable else 1  # POST/PUT/PATCH - только один раз
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return _read(r)
        except Exception as e:
            last = e
            # Первое соединение к workers.dev часто виснет, а свежее проходит
            if attempt + 1 < attempts:
                time.sleep(2)
                req = _build(path, payload, method, secret, None)
    raise last


def api_get(path, timeout=20, secret=None, retries=1):
    return api_call("GET", path, None, timeout, secret, retries)


def api_post(path, payload, timeout=20, secret=None, retries=0, method="POST"):
    # method нужен, когда вызывающий шлёт PUT (панели, контракты)
    return api_call(method, path, payload, timeout, secret, retries)


def api_delete(path, timeout=20, secret=None, retries=0):
    return api_call("DELETE", path, None, timeout, secret, retries)
