from datetime import date, datetime
from aiogram import Bot
from aiogram import Router, F
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, MessageOriginUser, MessageOriginHiddenUser
from bot.admin_bot import send_admins_list, appoint_admin, dismiss_admin
from bot.broadcast_bot import start_broadcast
from bot.coffeemaker_bot import (send_coffeemakers_list, send_all_users_in_details, add_coffeemaker, remove_coffeemaker_by_id,
                                 approve_feedback_for_user, add_feedback_link, correct_purchase_count_for_user,
                                 add_certificate_code, send_plan_next_week, add_subscription_for_user, send_shift_wishes)
from bot.planner import get_shift_wishes_text
from bot.schedule_bot import send_schedule_editor
from bot.payment_bot import send_payment_link
from db.feedback import get_feedbacks_waiting_approval
from db.purchases import get_count
from db.users import User, get_user, get_users, get_user_by_username
from keyboards.admin_panel import (SECTIONS, MAIN_SECTION, CANCEL_CALLBACK, CONFIRM_CALLBACK, SKIP_CALLBACK, CLOSE_CALLBACK,
                                   AdminSection, AdminAction, AdminPickUser, AdminUsersPage,
                                   get_admin_panel_keyboard, get_section_keyboard, get_users_keyboard,
                                   get_cancel_keyboard, get_confirm_keyboard)
from keyboards.schedule_keyboard import AdminWishesWeek, get_shift_wishes_keyboard
from keyboards.main_menu import ADMIN_PANEL_BUTTON
from utils.admin import is_admin, get_admin_ids
from utils.user_utils import get_user_name, get_coffeemaker_emoji

router = Router()


def from_admin(event: Message | CallbackQuery) -> bool:
  return is_admin(event.from_user.id)


# Все обработчики панели только для администраторов, остальные сообщения уходят в следующие роутеры
router.message.filter(from_admin)
router.callback_query.filter(from_admin)


class AdminPanelState(StatesGroup):
  choosing_user = State()
  confirming = State()
  entering_name = State()
  entering_count = State()
  entering_code = State()
  entering_link = State()


PANEL_TEXT = "🛠 <b>Админ-панель</b>\nВыберите раздел ⬇"

# Действия, для которых нужно выбрать пользователя: действие -> вопрос
USER_PROMPTS = {
  "send_message": "✉️ Кому отправить сообщение?",
  "correct_purchase_count": "🔢 У кого изменить количество накопленных напитков?",
  "add_subscription": "🎫 Кому добавить абонемент?",
  "add_coffeemaker": "➕ Кого назначить бариста?",
  "remove_coffeemaker": "➖ Кого убрать из бариста?",
  "approve_feedback": "👍 Чей отзыв подтвердить? В списке — отзывы, ожидающие модерации",
  "add_link": "🔗 Кому добавить ссылку на отзыв?",
  "add_admin": "➕ Кого назначить администратором?",
  "remove_admin": "➖ С кого снять роль администратора?",
}

# Действия, которые выполняются только после подтверждения: действие -> вопрос
CONFIRM_TEXTS = {
  "remove_coffeemaker": "Убрать {name} из бариста?",
  "add_admin": "Назначить {name} администратором?",
  "remove_admin": "Снять роль администратора с {name}?",
  "plan_next_week": "📅 Открыть приём пожеланий на следующую неделю и отправить бариста сообщение о планировании?",
}

# Списки, где пользователи отсортированы от новых к старым
NEWEST_FIRST_ACTIONS = {"send_message", "correct_purchase_count", "add_subscription", "add_coffeemaker", "add_link", "add_admin"}


async def edit_message(message: Message, text: str, reply_markup: InlineKeyboardMarkup | None = None):
  # Повторное нажатие той же кнопки не меняет сообщение — Telegram отвечает ошибкой, её можно игнорировать
  try:
    await message.edit_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
  except TelegramBadRequest:
    pass


def get_created_date(user: User) -> datetime:
  try:
    return datetime.strptime(user.created_date, "%d.%m.%Y %H:%M:%S")
  except (TypeError, ValueError):
    return datetime.min


def get_user_caption(user: User) -> str:
  return f"{get_coffeemaker_emoji(user)} {get_user_name(user)}".strip()


def get_candidates(action: str, admin_id: int, query: str | None = None) -> list[tuple[int, str]]:
  """
  Возвращает пользователей (id, подпись), из которых выбирают для действия. query — строка поиска по имени.
  """
  if action == "remove_admin":
    candidates = [(admin, get_user_name(get_user(admin)) or str(admin)) for admin in get_admin_ids() if admin != admin_id]
  else:
    if action == "remove_coffeemaker":
      users = [user for user in get_users() if user.is_coffeemaker]
    elif action == "approve_feedback":
      users = [get_user(feedback.user_id) for feedback in get_feedbacks_waiting_approval()]
      users = [user for user in users if user is not None]
    else:
      users = get_users()
      if action == "add_coffeemaker":
        users = [user for user in users if not user.is_coffeemaker]
      elif action == "add_admin":
        users = [user for user in users if not is_admin(user.id)]
    if action in NEWEST_FIRST_ACTIONS:
      users = sorted(users, key=get_created_date, reverse=True)
    candidates = [(int(user.id), get_user_caption(user)) for user in users]
  if query:
    candidates = [(user_id, text) for user_id, text in candidates if query.lower() in text.lower()]
  return candidates


def get_choose_user_text(action: str, candidates: list[tuple[int, str]], query: str | None = None) -> str:
  text = USER_PROMPTS[action] + "\n\n"
  if query:
    text += f"🔍 Найдено по запросу «{query}»: {len(candidates)}\n" if candidates else f"🔍 По запросу «{query}» никого не нашлось\n"
  elif not candidates:
    text += "Список пуст 🤷\n"
  else:
    text += "Выберите пользователя из списка" + (" (сначала новые)" if action in NEWEST_FIRST_ACTIONS else "") + ".\n"
  text += "Или отправьте ID, @username, часть имени для поиска или перешлите сообщение пользователя ⬇"
  return text


async def open_admin_panel(message: Message, state: FSMContext):
  await state.clear()
  await message.answer(PANEL_TEXT, reply_markup=get_admin_panel_keyboard(), parse_mode=ParseMode.HTML)


@router.message(Command('admin'))
async def handle_admin_command(message: Message, state: FSMContext):
  await open_admin_panel(message, state)


@router.message(F.text.lower() == ADMIN_PANEL_BUTTON.lower())
async def handle_admin_panel_button(message: Message, state: FSMContext):
  await open_admin_panel(message, state)


def is_not_command(message: Message) -> bool:
  return not (message.text or "").startswith("/")


@router.message(StateFilter(AdminPanelState), F.text.startswith("/"))
async def leave_panel_on_command(message: Message, state: FSMContext):
  # Набранная команда прерывает ввод в панели и обрабатывается как обычно.
  # Обработчики ввода ниже пропускают команды (is_not_command), поэтому она уйдёт в следующие роутеры
  await state.clear()
  raise SkipHandler()


@router.callback_query(AdminSection.filter())
async def handle_section(query: CallbackQuery, callback_data: AdminSection):
  if callback_data.name == MAIN_SECTION:
    await edit_message(query.message, PANEL_TEXT, get_admin_panel_keyboard())
  else:
    title = SECTIONS[callback_data.name][0]
    await edit_message(query.message, f"{title}\nВыберите действие ⬇", get_section_keyboard(callback_data.name))
  await query.answer()


@router.callback_query(F.data == CLOSE_CALLBACK)
async def handle_close(query: CallbackQuery, state: FSMContext):
  await state.clear()
  await query.message.delete()
  await query.answer()


@router.callback_query(AdminAction.filter())
async def handle_action(query: CallbackQuery, callback_data: AdminAction, state: FSMContext, bot: Bot):
  action = callback_data.name
  # Убираем «часики» на кнопке сразу: некоторые действия выполняются долго
  await query.answer()
  await state.clear()
  if action == "all_users_in_details":
    await send_all_users_in_details(query.message)
  elif action == "coffeemakers":
    await send_coffeemakers_list(query.message)
  elif action == "admins":
    await send_admins_list(query.message)
  elif action == "shift_wishes":
    await send_shift_wishes(query.message)
  elif action == "schedule":
    await send_schedule_editor(query.message)
  elif action == "payment_link":
    await send_payment_link(query.message)
  elif action == "broadcast":
    await start_broadcast(query.message, state)
  elif action == "plan_next_week":
    await state.update_data(action=action)
    await query.message.answer(CONFIRM_TEXTS[action], reply_markup=get_confirm_keyboard())
    await state.set_state(AdminPanelState.confirming)
  elif action == "add_code":
    await query.message.answer("🔐 Введите 8-значный код сертификата ⬇", reply_markup=get_cancel_keyboard())
    await state.set_state(AdminPanelState.entering_code)
  elif action in USER_PROMPTS:
    candidates = get_candidates(action, query.from_user.id)
    await state.update_data(action=action)
    await query.message.answer(get_choose_user_text(action, candidates), reply_markup=get_users_keyboard(candidates))
    await state.set_state(AdminPanelState.choosing_user)


@router.callback_query(AdminWishesWeek.filter())
async def handle_wishes_week(query: CallbackQuery, callback_data: AdminWishesWeek):
  week_start = date.fromisoformat(callback_data.week)
  await edit_message(query.message, get_shift_wishes_text(week_start), get_shift_wishes_keyboard(week_start))
  await query.answer()


@router.callback_query(AdminPanelState.choosing_user, AdminUsersPage.filter())
async def handle_users_page(query: CallbackQuery, callback_data: AdminUsersPage, state: FSMContext):
  data = await state.get_data()
  candidates = get_candidates(data.get("action"), query.from_user.id, data.get("query"))
  await edit_message(query.message, get_choose_user_text(data.get("action"), candidates, data.get("query")),
                     get_users_keyboard(candidates, callback_data.page))
  await query.answer()


@router.callback_query(AdminPanelState.choosing_user, AdminPickUser.filter())
async def handle_pick_user(query: CallbackQuery, callback_data: AdminPickUser, state: FSMContext, bot: Bot):
  await query.answer()
  await query.message.edit_reply_markup(reply_markup=None)  # Убираем список, чтобы не выбрать дважды
  await select_user(query.message, state, bot, query.from_user.id, callback_data.user_id)


@router.message(AdminPanelState.choosing_user, is_not_command)
async def handle_user_input(message: Message, state: FSMContext, bot: Bot):
  data = await state.get_data()
  action = data.get("action")
  text = (message.text or "").strip()
  origin = message.forward_origin
  if isinstance(origin, MessageOriginUser):
    user_id = origin.sender_user.id
  elif isinstance(origin, MessageOriginHiddenUser):
    await message.answer("⚠️ Пользователь скрыл свой аккаунт при пересылке. Найдите его по имени или выберите из списка")
    return
  elif text.isdigit():
    user_id = int(text)
  elif text.startswith("@"):
    user = get_user_by_username(text[1:])
    if user is None:
      await message.answer("❌ Пользователь с таким username не найден!")
      return
    user_id = int(user.id)
  elif text:
    candidates = get_candidates(action, message.from_user.id, text)
    if len(candidates) == 1:
      user_id = candidates[0][0]
    else:
      await state.update_data(query=text)
      await message.answer(get_choose_user_text(action, candidates, text), reply_markup=get_users_keyboard(candidates))
      return
  else:
    await message.answer("⚠️ Отправьте ID, @username или часть имени пользователя")
    return
  await select_user(message, state, bot, message.from_user.id, user_id)


async def select_user(message: Message, state: FSMContext, bot: Bot, admin_id: int, user_id: int):
  """
  Продолжает действие после выбора пользователя: запрашивает подтверждение, следующий параметр или сразу выполняет.
  """
  data = await state.get_data()
  action = data.get("action")
  user = get_user(user_id)
  # Снять роль администратора можно и с того, кто не запускал бота
  if user is None and action != "remove_admin":
    await message.answer("❌ Такого пользователя нет в боте! Пользователь должен сначала запустить бота")
    return
  name = get_user_name(user) or str(user_id)
  await state.update_data(user_id=user_id)

  if action in CONFIRM_TEXTS:
    await message.answer(CONFIRM_TEXTS[action].format(name=name), reply_markup=get_confirm_keyboard())
    await state.set_state(AdminPanelState.confirming)
  elif action == "send_message":
    await start_broadcast(message, state, user_id)
  elif action == "correct_purchase_count":
    count = get_count(user_id) or 0
    await message.answer(f"🔢 У пользователя {name} накоплено {count} из 6.\nВведите новое количество напитков (от 0 до 6) ⬇",
                         reply_markup=get_cancel_keyboard())
    await state.set_state(AdminPanelState.entering_count)
  elif action == "add_coffeemaker":
    await message.answer(f"☕ Введите имя бариста для {name} или нажмите «Пропустить» ⬇",
                         reply_markup=get_cancel_keyboard(with_skip=True))
    await state.set_state(AdminPanelState.entering_name)
  elif action == "add_link":
    await message.answer(f"🔗 Отправьте ссылку на отзыв пользователя {name} ⬇", reply_markup=get_cancel_keyboard())
    await state.set_state(AdminPanelState.entering_link)
  elif action == "add_subscription":
    await state.clear()
    await add_subscription_for_user(message, bot, user_id)
  elif action == "approve_feedback":
    await state.clear()
    await approve_feedback_for_user(message, bot, user_id)


@router.callback_query(AdminPanelState.confirming, F.data == CONFIRM_CALLBACK)
async def handle_confirm(query: CallbackQuery, state: FSMContext, bot: Bot):
  data = await state.get_data()
  await state.clear()
  await query.answer()
  await query.message.edit_reply_markup(reply_markup=None)  # Убираем кнопки
  action = data.get("action")
  user_id = data.get("user_id")
  if action == "remove_coffeemaker":
    await remove_coffeemaker_by_id(query.message, user_id)
  elif action == "add_admin":
    await appoint_admin(query.message, bot, query.from_user.id, user_id)
  elif action == "remove_admin":
    await dismiss_admin(query.message, bot, query.from_user.id, user_id)
  elif action == "plan_next_week":
    await send_plan_next_week(query.message, bot)


@router.callback_query(AdminPanelState.entering_name, F.data == SKIP_CALLBACK)
async def handle_skip_name(query: CallbackQuery, state: FSMContext, bot: Bot):
  data = await state.get_data()
  await state.clear()
  await query.answer()
  await query.message.edit_reply_markup(reply_markup=None)  # Убираем кнопки
  await add_coffeemaker(query.message, bot, data.get("user_id"))


@router.message(AdminPanelState.entering_name, is_not_command)
async def handle_name_input(message: Message, state: FSMContext, bot: Bot):
  name = (message.text or "").strip()
  if not name:
    await message.answer("⚠️ Отправьте имя текстом или нажмите «Пропустить»")
    return
  data = await state.get_data()
  await state.clear()
  await add_coffeemaker(message, bot, data.get("user_id"), name)


@router.message(AdminPanelState.entering_count, is_not_command)
async def handle_count_input(message: Message, state: FSMContext):
  data = await state.get_data()
  # При некорректном вводе остаёмся в этом шаге, чтобы можно было ввести число ещё раз
  if await correct_purchase_count_for_user(message, data.get("user_id"), (message.text or "").strip()):
    await state.clear()


@router.message(AdminPanelState.entering_code, is_not_command)
async def handle_code_input(message: Message, state: FSMContext):
  if await add_certificate_code(message, message.from_user.id, (message.text or "").strip()):
    await state.clear()


@router.message(AdminPanelState.entering_link, is_not_command)
async def handle_link_input(message: Message, state: FSMContext):
  link = (message.text or "").strip()
  if not link:
    await message.answer("⚠️ Отправьте ссылку текстом")
    return
  data = await state.get_data()
  await state.clear()
  await add_feedback_link(message, data.get("user_id"), link)


@router.callback_query(F.data == CANCEL_CALLBACK)
async def handle_cancel(query: CallbackQuery, state: FSMContext):
  await state.clear()
  await query.message.edit_reply_markup(reply_markup=None)  # Убираем кнопки
  await query.message.answer("Действие отменено ❌")
  await query.answer()


@router.callback_query(F.data.startswith("adm_"))
async def handle_outdated_callback(query: CallbackQuery):
  # Кнопка из старого сообщения: состояние уже сброшено (другое действие или перезапуск бота)
  await query.answer("Действие устарело. Откройте админ-панель заново: /admin", show_alert=True)
