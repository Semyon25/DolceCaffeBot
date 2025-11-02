from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

def get_next_week_range(separator="."):
    today = datetime.today()
    weekday = today.weekday()

    days_until_next_monday = 7 - weekday
    next_monday = today + timedelta(days=days_until_next_monday)
    next_sunday = next_monday + timedelta(days=6)

    start_str = next_monday.strftime(f"%d{separator}%m")
    end_str = next_sunday.strftime(f"%d{separator}%m")

    return start_str, end_str

def today():
    return datetime.now(ZoneInfo("Europe/Moscow")).date()