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

# Код смены — "{день}_{время}", например "mon_10_16". Так смены хранятся в БД.
# Все смены недели по порядку: Пн 10-16, Пн 16-22, Вт 10-16, ...
ALL_SHIFTS = [
    f"{day}_{time}"
    for day, _ in sorted(DAY_ORDER.items(), key=lambda x: x[1][0])
    for time, _ in sorted(TIME_ORDER.items(), key=lambda x: x[1][0])
]


def parse_shift(shift: str) -> tuple[str, str]:
    """Делит код смены "mon_10_16" на день "mon" и время "10_16" """
    day, time = shift.split("_", 1)
    return day, time


def format_shift(shift: str) -> str:
    day, time = parse_shift(shift)
    _, day_name = DAY_ORDER[day]
    _, time_name = TIME_ORDER[time]
    return f"{day_name} {time_name}"


def sort_shifts(shifts: list[str]) -> list[str]:
    """Оставляет только известные смены без повторов и сортирует их по дням и времени"""
    return [shift for shift in ALL_SHIFTS if shift in shifts]


def order_and_format_shifts(shifts: list[str]) -> list[str]:
    return [format_shift(shift) for shift in sort_shifts(shifts)]
