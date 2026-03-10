import re
from datetime import datetime, timedelta


def parse_schedule(text: str):

    result = {}

    m = re.search(r"с (\d{2}\.\d{2}) по (\d{2}\.\d{2})", text)

    if not m:
        return result

    start_str, end_str = m.groups()

    year = datetime.now().year

    start_date = datetime.strptime(
        f"{start_str}.{year}", "%d.%m.%Y"
    ).date()

    end_date = datetime.strptime(
        f"{end_str}.{year}", "%d.%m.%Y"
    ).date()

    lines = text.splitlines()

    day_employees = {}

    for line in lines:

        m = re.match(r"(Пн|Вт|Ср|Чт|Пт|Сб|Вс):(.+)", line.strip())

        if not m:
            continue

        day, shifts = m.groups()

        matches = re.findall(
            r"\d{1,2}-\d{1,2}\s+([А-Яа-яA-Za-z]+)",
            shifts,
        )

        if not matches:
            continue

        day_employees[day] = matches[-1]

    days = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]

    d = start_date

    while d <= end_date:

        weekday = days[d.weekday()]

        employee = day_employees.get(weekday)

        if employee:
            result[d] = employee

        d += timedelta(days=1)

    return result