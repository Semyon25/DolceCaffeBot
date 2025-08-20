from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.shifts import DAY_ORDER, TIME_ORDER, format_shift

def get_shifts_keyboard(
    selected: list[str] | None = None,
    join_bottom: bool = False,  # если True — кнопки "Без смен" и "Отправить" будут в одной строке
) -> InlineKeyboardMarkup:
    """Создает клавиатуру с галочками"""
    if selected is None:
        selected = []

    keyboard = []

    # Список всех смен (отсортирован)
    all_shifts = []
    for day, (day_order, day_name) in DAY_ORDER.items():
        for time, (time_order, time_name) in TIME_ORDER.items():
            cb_data = f"shift_{day}_{time}"
            all_shifts.append(((day_order, time_order), cb_data))

    all_shifts.sort(key=lambda x: x[0])

    # Собираем по 2 смены в день
    for i in range(0, len(all_shifts), 2):
        row = []
        for _, cb_data in all_shifts[i:i+2]:
            nice_text = format_shift(cb_data)
            text = f"✅ {nice_text}" if cb_data in selected else nice_text
            row.append(InlineKeyboardButton(text=text, callback_data=cb_data))
        keyboard.append(row)

    # Нижние кнопки
    if join_bottom:
        keyboard.append([
            InlineKeyboardButton(text="❌ Без смен", callback_data="shift_none"),
            InlineKeyboardButton(text="✅ Отправить", callback_data="shift_submit"),
        ])
    else:
        keyboard.append([InlineKeyboardButton(text="❌ Без смен", callback_data="shift_none")])
        keyboard.append([InlineKeyboardButton(text="✅ Отправить", callback_data="shift_submit")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)