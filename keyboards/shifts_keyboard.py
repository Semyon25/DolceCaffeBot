from datetime import date
from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.shifts import ALL_SHIFTS, format_shift

SELECTED_MARK = "✅ "
NO_SHIFTS_ACTION = "none"
SUBMIT_ACTION = "submit"


class ShiftCallback(CallbackData, prefix="shf"):
    week: str  # Понедельник недели, ГГГГ-ММ-ДД
    action: str  # Код смены, NO_SHIFTS_ACTION или SUBMIT_ACTION


def get_shifts_keyboard(week_start: date, selected: list[str] | None = None, submitted: bool = False) -> InlineKeyboardMarkup:
    """Создает клавиатуру выбора смен на неделю с галочками. submitted — бариста уже отправлял выбор."""
    if selected is None:
        selected = []
    week = week_start.isoformat()

    keyboard = []
    # По 2 смены в день
    for i in range(0, len(ALL_SHIFTS), 2):
        row = []
        for shift in ALL_SHIFTS[i:i+2]:
            text = format_shift(shift)
            if shift in selected:
                text = SELECTED_MARK + text
            row.append(InlineKeyboardButton(text=text, callback_data=ShiftCallback(week=week, action=shift).pack()))
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton(text="❌ Без смен", callback_data=ShiftCallback(week=week, action=NO_SHIFTS_ACTION).pack())])
    submit_text = "✅ Отправить изменения" if submitted else "✅ Отправить"
    keyboard.append([InlineKeyboardButton(text=submit_text, callback_data=ShiftCallback(week=week, action=SUBMIT_ACTION).pack())])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_selected_shifts(markup: InlineKeyboardMarkup | None) -> list[str]:
    """Смены, отмеченные галочкой на клавиатуре сообщения. Отметки до отправки хранятся только в самой клавиатуре."""
    selected = []
    if markup is None:
        return selected
    for row in markup.inline_keyboard:
        for button in row:
            if not button.text.startswith(SELECTED_MARK) or not button.callback_data:
                continue
            try:
                action = ShiftCallback.unpack(button.callback_data).action
            except (TypeError, ValueError):
                continue
            if action in ALL_SHIFTS:
                selected.append(action)
    return selected
