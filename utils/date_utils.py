from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

MOSCOW_TZ = ZoneInfo("Europe/Moscow")

def now():
    return datetime.now(MOSCOW_TZ)

def today():
    return now().date()

def get_week_start(day: date) -> date:
    """Понедельник недели, в которую входит day"""
    return day - timedelta(days=day.weekday())

def get_next_week_start() -> date:
    """Понедельник следующей недели по московскому времени"""
    return get_week_start(today()) + timedelta(days=7)

def get_week_range(week_start: date, separator=".") -> tuple[str, str]:
    """Даты понедельника и воскресенья недели в виде строк ДД{separator}ММ"""
    week_end = week_start + timedelta(days=6)
    return week_start.strftime(f"%d{separator}%m"), week_end.strftime(f"%d{separator}%m")
