from datetime import datetime, timedelta

def get_next_week_range():
    today = datetime.today()
    weekday = today.weekday()

    days_until_next_monday = 7 - weekday
    next_monday = today + timedelta(days=days_until_next_monday)
    next_sunday = next_monday + timedelta(days=6)

    # Преобразуем в строку формата "дд.мм"
    start_str = next_monday.strftime("%d.%m")
    end_str = next_sunday.strftime("%d.%m")

    return start_str, end_str