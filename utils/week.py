from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from zoneinfo import ZoneInfo

MSK = ZoneInfo("Europe/Moscow")

def prev_week_range_msk():
    # берём "сейчас", сдвигаем на -7 дней и считаем неделю
    now = datetime.utcnow()
    return week_range_msk(now - timedelta(days=7))


def week_range_msk(dt_utc: datetime | None = None):
    """
    Возвращает (week_start, week_end) в формате YYYY-MM-DD по МСК.
    week_start = понедельник, week_end = воскресенье.
    """
    if dt_utc is None:
        dt_utc = datetime.utcnow()
    dt = dt_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(MSK)

    # Monday = 0 ... Sunday = 6
    start = (dt - timedelta(days=dt.weekday())).date()
    end = (start + timedelta(days=6))
    return start.isoformat(), end.isoformat()
