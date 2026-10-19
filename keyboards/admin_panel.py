from datetime import date, timedelta
from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Количество пользователей на одной странице списка выбора
USERS_PER_PAGE = 8
# Максимальная длина текста кнопки с именем пользователя
MAX_USER_BUTTON_LENGTH = 40

CANCEL_CALLBACK = "adm_cancel"
CONFIRM_CALLBACK = "adm_confirm"
SKIP_CALLBACK = "adm_skip"
CLOSE_CALLBACK = "adm_close"
MAIN_SECTION = "main"


class AdminSection(CallbackData, prefix="adm_section"):
  name: str


class AdminAction(CallbackData, prefix="adm_action"):
  name: str


class AdminPickUser(CallbackData, prefix="adm_user"):
  user_id: int


class AdminUsersPage(CallbackData, prefix="adm_page"):
  page: int


class AdminWishesWeek(CallbackData, prefix="adm_wishes"):
  week: str  # Понедельник недели, ГГГГ-ММ-ДД


# Разделы панели: код раздела -> (заголовок, [(текст кнопки, действие), ...])
SECTIONS = {
  "users": ("👥 Пользователи", [
    ("📋 Все пользователи", "all_users_in_details"),
    ("✉️ Написать пользователю", "send_message"),
    ("🔢 Изменить накопленные напитки", "correct_purchase_count"),
    ("🎫 Добавить абонемент", "add_subscription"),
  ]),
  "coffeemakers": ("☕ Бариста", [
    ("📋 Список бариста", "coffeemakers"),
    ("➕ Добавить бариста", "add_coffeemaker"),
    ("➖ Удалить бариста", "remove_coffeemaker"),
    ("📅 Запланировать следующую неделю", "plan_next_week"),
    ("🗓 Пожелания по сменам", "shift_wishes"),
  ]),
  "codes": ("🎟 Коды и отзывы", [
    ("🔐 Добавить код сертификата", "add_code"),
    ("👍 Подтвердить отзыв", "approve_feedback"),
    ("🔗 Добавить ссылку на отзыв", "add_link"),
  ]),
  "admins": ("👑 Администраторы", [
    ("📋 Список администраторов", "admins"),
    ("➕ Назначить администратора", "add_admin"),
    ("➖ Снять администратора", "remove_admin"),
  ]),
}


def get_admin_panel_keyboard() -> InlineKeyboardMarkup:
  kb = InlineKeyboardBuilder()
  kb.button(text=SECTIONS["users"][0], callback_data=AdminSection(name="users"))
  kb.button(text=SECTIONS["coffeemakers"][0], callback_data=AdminSection(name="coffeemakers"))
  kb.button(text="📢 Рассылка всем", callback_data=AdminAction(name="broadcast"))
  kb.button(text=SECTIONS["codes"][0], callback_data=AdminSection(name="codes"))
  kb.button(text=SECTIONS["admins"][0], callback_data=AdminSection(name="admins"))
  kb.button(text="💳 Оплата бота", callback_data=AdminAction(name="payment_link"))
  kb.button(text="✖️ Закрыть", callback_data=CLOSE_CALLBACK)
  kb.adjust(2, 2, 2, 1)
  return kb.as_markup()


def get_section_keyboard(section: str) -> InlineKeyboardMarkup:
  kb = InlineKeyboardBuilder()
  for text, action in SECTIONS[section][1]:
    kb.button(text=text, callback_data=AdminAction(name=action))
  kb.button(text="⬅️ Назад", callback_data=AdminSection(name=MAIN_SECTION))
  kb.adjust(1)
  return kb.as_markup()


def get_users_keyboard(users: list[tuple[int, str]], page: int = 0) -> InlineKeyboardMarkup:
  """
  Клавиатура выбора пользователя из списка (id, подпись) с постраничной навигацией.
  """
  kb = InlineKeyboardBuilder()
  pages = max(1, (len(users) + USERS_PER_PAGE - 1) // USERS_PER_PAGE)
  page = min(max(page, 0), pages - 1)
  for user_id, text in users[page * USERS_PER_PAGE:(page + 1) * USERS_PER_PAGE]:
    if len(text) > MAX_USER_BUTTON_LENGTH:
      text = text[:MAX_USER_BUTTON_LENGTH - 1] + "…"
    kb.row(InlineKeyboardButton(text=text, callback_data=AdminPickUser(user_id=user_id).pack()))
  if pages > 1:
    kb.row(
      InlineKeyboardButton(text="◀️", callback_data=AdminUsersPage(page=(page - 1) % pages).pack()),
      InlineKeyboardButton(text=f"{page + 1} / {pages}", callback_data=AdminUsersPage(page=page).pack()),
      InlineKeyboardButton(text="▶️", callback_data=AdminUsersPage(page=(page + 1) % pages).pack()),
    )
  kb.row(InlineKeyboardButton(text="❌ Отмена", callback_data=CANCEL_CALLBACK))
  return kb.as_markup()


def get_cancel_keyboard(with_skip: bool = False) -> InlineKeyboardMarkup:
  buttons = []
  if with_skip:
    buttons.append(InlineKeyboardButton(text="➡️ Пропустить", callback_data=SKIP_CALLBACK))
  buttons.append(InlineKeyboardButton(text="❌ Отмена", callback_data=CANCEL_CALLBACK))
  return InlineKeyboardMarkup(inline_keyboard=[buttons])


def get_confirm_keyboard() -> InlineKeyboardMarkup:
  return InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton(text="✅ Да", callback_data=CONFIRM_CALLBACK),
    InlineKeyboardButton(text="❌ Отмена", callback_data=CANCEL_CALLBACK),
  ]])


def get_shift_wishes_keyboard(week_start: date) -> InlineKeyboardMarkup:
  """Переключение недель в сводке пожеланий бариста"""
  return InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton(text="◀️ Пред. неделя", callback_data=AdminWishesWeek(week=(week_start - timedelta(days=7)).isoformat()).pack()),
    InlineKeyboardButton(text="🔄", callback_data=AdminWishesWeek(week=week_start.isoformat()).pack()),
    InlineKeyboardButton(text="След. неделя ▶️", callback_data=AdminWishesWeek(week=(week_start + timedelta(days=7)).isoformat()).pack()),
  ]])
