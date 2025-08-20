DAY_ORDER = {
    "mon": (1, "Пн"),
    "tue": (2, "Вт"),
    "wed": (3, "Ср"),
    "thu": (4, "Чт"),
    "fri": (5, "Пт"),
    "sat": (6, "Сб"),
    "sun": (7, "Вс"),
}

TIME_ORDER = {
    "10_16": (1, "10-16"),
    "16_22": (2, "16-22"),
}


def format_shift(shift: str) -> str:
    parts = shift.split("_")  # ['shift', 'mon', '10', '16']
    day = parts[1]
    time = "_".join(parts[2:])  # "10_16"
    _, day_name = DAY_ORDER[day]
    _, time_name = TIME_ORDER[time]
    return f"{day_name} {time_name}"


def order_and_format_shifts(shifts: list[str]) -> list[str]:
    parsed = []
    for shift in shifts:
        try:
            parts = shift.split("_")  # ['shift', 'mon', '10', '16']
            day = parts[1]
            time = "_".join(parts[2:])  # "10_16"
            day_order, day_name = DAY_ORDER[day]
            time_order, time_name = TIME_ORDER[time]
            parsed.append(((day_order, time_order), f"{day_name} {time_name}"))
        except Exception:
            continue

    parsed.sort(key=lambda x: x[0])
    return [p[1] for p in parsed]
