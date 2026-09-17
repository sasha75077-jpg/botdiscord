import gspread
from config import SHEET_ID, SHEET_CREDENTIALS, CONTRACTS_SHEET
from database import insert_contract_if_new_sync


def get_sheets_client():
    return gspread.service_account(filename=SHEET_CREDENTIALS)


def ddmmyyyy_to_iso(s: str) -> str:
    s = (s or "").strip()
    if not s or len(s.split('-')) != 3:
        return ""
    dd, mm, yyyy = s.split("-")
    return f"{yyyy}-{mm.zfill(2)}-{dd.zfill(2)}"


def to_int(v, default=0):
    try:
        if v is None or str(v).strip() == "":
            return default
        return int(float(v))
    except Exception:
        return default


def to_str(v):
    return "" if v is None else str(v).strip()


def is_yes(v):
    return to_str(v).upper() == "YES"


def poll_contracts(guild_id: str, sheet_id: str = None, credentials_path: str = None):
    """
    Импорт контрактов из Google Sheets для конкретного сервера

    Args:
        guild_id: ID Discord сервера
        sheet_id: ID Google таблицы (если None, берется из config.SHEET_ID)
        credentials_path: Путь к credentials.json (если None, берется из config.SHEET_CREDENTIALS)
    """
    # Использовать параметры или значения по умолчанию из config
    _sheet_id = sheet_id or SHEET_ID
    _credentials = credentials_path or SHEET_CREDENTIALS

    if not _sheet_id:
        print(f"[Guild {guild_id}] SHEET_ID не настроен, пропускаем импорт")
        return 0

    try:
        gc = gspread.service_account(filename=_credentials)
        sh = gc.open_by_key(_sheet_id)
        ws = sh.worksheet(CONTRACTS_SHEET)
    except Exception as e:
        print(f"[Guild {guild_id}] Ошибка подключения к Google Sheets: {e}")
        return 0

    rows = ws.get_all_records()
    imported = 0

    for row in rows:
        status = to_str(row.get("status")).upper()
        if status not in {"NEW", "POSTED"}:
            continue

        normalized = {
            "guild_id": guild_id,  # Добавлен guild_id
            "ts": row.get("ts"),
            "discord_id": to_str(row.get("discord_id")),
            "contract_type": to_str(row.get("contract_type")),
            "channel_id": to_str(row.get("channel_id")),
            "discord_message_id": to_str(row.get("discord_message_id")),
            "attachment_urls": to_str(row.get("attachment_urls")),
            "msk_date": to_str(row.get("msk_date")),
            "details": to_str(row.get("details")),
            "price": to_int(row.get("price")),
            "fish_type": to_str(row.get("fish_type")),
            "fish_qty": to_int(row.get("fish_qty")),
            "ore_type": to_str(row.get("ore_type")),
            "m_iron": to_int(row.get("m_iron")),
            "m_silver": to_int(row.get("m_silver")),
            "m_copper": to_int(row.get("m_copper")),
            "m_tin": to_int(row.get("m_tin")),
            "m_gold": to_int(row.get("m_gold")),
            "goods_delivery": is_yes(row.get("goods_delivery")),
            "goods_loading": is_yes(row.get("goods_loading")),
            "atelier_total_uniforms": to_int(row.get("atelier_total_uniforms")),
            "marketplace_links_count": to_int(row.get("marketplace_links_count")),
            "wn_category": to_str(row.get("wn_category")),
            "wn_screenshots_count": to_int(row.get("wn_screenshots_count")),
            "tuning_has_screenshot": is_yes(row.get("tuning_has_screenshot")),
            "msk_date_iso": ddmmyyyy_to_iso(to_str(row.get("msk_date"))),
            "status": status,
        }

        try:
            insert_contract_if_new_sync(normalized)
            imported += 1
        except Exception as e:
            print(f"[Guild {guild_id}] Failed to insert contract: {e}")

    return imported

