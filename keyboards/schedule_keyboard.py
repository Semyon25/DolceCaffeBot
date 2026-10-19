from datetime import date, timedelta
from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Максимальная длина текста кнопки с именем бариста
MAX_BUTTON_LENGTH = 40

# Особые значения user_id в ScheduleAssign
NOBODY = 0  # Никого не ставить на смену
RESET = -1  # Отменить неопубликованную правку смены

PUBLISH_ACTION = "publish"
CONFIRM_PUBLISH_ACTION = "confirm"
DISCARD_ACTION = "discard"


class AdminWishesWeek(CallbackData, prefix="adm_wishes"):
  week: str  # Понедельник недели, ГГГГ-ММ-ДД


class ScheduleWeek(CallbackData, prefix="sch"):
  week: str


class ScheduleShift(CallbackData, prefix="sch_shift"):
  week: str
  shift: str


class ScheduleAssign(CallbackData, prefix="sch_assign"):
  week: str
  shift: str
  user_id: int  # Бариста, NOBODY или RESET


class ScheduleAction(CallbackData, prefix="sch_action"):
  week: str
  action: str  # PUBLISH_ACTION, CONFIRM_PUBLISH_ACTION или DISCARD_ACTION


def shorten(text: str) -> str:
  return text if len(text) <= MAX_BUTTON_LENGTH else text[:MAX_BUTTON_LENGTH - 1] + "…"


def get_week_navigation(week_start: date, callback) -> list[InlineKeyboardButton]:
  """Переключение недель: callback(week) — данные кнопки для недели"""
  return [
    InlineKeyboardButton(text="◀️ Пред. неделя", callback_data=callback((week_start - timedelta(days=7)).isoformat()).pack()),
    InlineKeyboardButton(text="🔄", callback_data=callback(week_start.isoformat()).pack()),
    InlineKeyboardButton(text="След. неделя ▶️", callback_data=callback((week_start + timedelta(days=7)).isoformat()).pack()),
  ]


def get_shift_wishes_keyboard(week_start: date) -> InlineKeyboardMarkup:
  """Переключение недель в сводке пожеланий бариста"""
  return InlineKeyboardMarkup(inline_keyboard=[
    get_week_navigation(week_start, lambda week: AdminWishesWeek(week=week)),
    [InlineKeyboardButton(text="📝 Расписание на эту неделю", callback_data=ScheduleWeek(week=week_start.isoformat()).pack())],
  ])


def get_schedule_editor_keyboard(week_start: date, shift_buttons: list[tuple[str, str]], read_only: bool,
                                 publish_text: str | None, discard_text: str | None) -> InlineKeyboardMarkup:
  """
  Редактор расписания. shift_buttons — (код смены, текст кнопки) по порядку смен.
  publish_text, discard_text — тексты кнопок публикации и сброса правок или None, если кнопки не нужны.
  """
  week = week_start.isoformat()
  kb = InlineKeyboardBuilder()
  if not read_only:
    # По 2 смены в день
    for i in range(0, len(shift_buttons), 2):
      kb.row(*[InlineKeyboardButton(text=shorten(text), callback_data=ScheduleShift(week=week, shift=shift).pack())
               for shift, text in shift_buttons[i:i + 2]])
    if publish_text:
      kb.row(InlineKeyboardButton(text=publish_text, callback_data=ScheduleAction(week=week, action=PUBLISH_ACTION).pack()))
    if discard_text:
      kb.row(InlineKeyboardButton(text=discard_text, callback_data=ScheduleAction(week=week, action=DISCARD_ACTION).pack()))
  kb.row(InlineKeyboardButton(text="🙋 Пожелания бариста", callback_data=AdminWishesWeek(week=week).pack()))
  kb.row(*get_week_navigation(week_start, lambda week: ScheduleWeek(week=week)))
  return kb.as_markup()


def get_shift_picker_keyboard(week_start: date, shift: str, candidates: list[tuple[int, str]],
                              nobody_selected: bool, can_reset: bool) -> InlineKeyboardMarkup:
  """Выбор бариста на смену. candidates — (id, текст кнопки)."""
  week = week_start.isoformat()
  kb = InlineKeyboardBuilder()
  for user_id, text in candidates:
    kb.row(InlineKeyboardButton(text=shorten(text), callback_data=ScheduleAssign(week=week, shift=shift, user_id=user_id).pack()))
  kb.row(InlineKeyboardButton(text=("✅ " if nobody_selected else "") + "🚫 Никого",
                              callback_data=ScheduleAssign(week=week, shift=shift, user_id=NOBODY).pack()))
  if can_reset:
    kb.row(InlineKeyboardButton(text="↩️ Отменить правку", callback_data=ScheduleAssign(week=week, shift=shift, user_id=RESET).pack()))
  kb.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=ScheduleWeek(week=week).pack()))
  return kb.as_markup()


def get_publish_confirm_keyboard(week_start: date) -> InlineKeyboardMarkup:
  week = week_start.isoformat()
  return InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton(text="✅ Опубликовать", callback_data=ScheduleAction(week=week, action=CONFIRM_PUBLISH_ACTION).pack()),
    InlineKeyboardButton(text="⬅️ Назад", callback_data=ScheduleWeek(week=week).pack()),
  ]])
