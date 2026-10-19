import asyncio
import html
from datetime import date, datetime, time, timedelta
from aiogram import Bot
from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup
from db.shift_wishes import open_planning_week, is_planning_week_opened, get_shift_wish, save_shift_wish, get_shift_wishes
from db.users import User, get_users, get_user
from keyboards.main_menu import MY_SHIFTS_BUTTON
from keyboards.shifts_keyboard import ShiftCallback, NO_SHIFTS_ACTION, SUBMIT_ACTION, get_shifts_keyboard, get_selected_shifts
from utils.date_utils import MOSCOW_TZ, now, today, get_week_start, get_next_week_start, get_week_range
from utils.user_utils import get_user_name
from utils.shifts import ALL_SHIFTS, format_shift, sort_shifts, order_and_format_shifts
from utils.send_message import notify_admin_and_managers

router = Router()

# Задержка между отправками сообщений в секундах (чтобы не превысить лимиты Telegram)
DELAY_BETWEEN_MESSAGES = 1

# Приём пожеланий на неделю открывается в пятницу перед ней в 15:00 и длится до конца воскресенья
OPENING_DAYS_BEFORE_WEEK = 3
OPENING_TIME = time(15, 0)

GREETING = "👋 Добрый день!\n\n📅 Давайте запланируем ваш график на следующую неделю."
REMINDER = "⏰ Напоминаем: вы ещё не выбрали смены на следующую неделю."


def get_planning_opening(week_start: date) -> datetime:
  return datetime.combine(week_start - timedelta(days=OPENING_DAYS_BEFORE_WEEK), OPENING_TIME, tzinfo=MOSCOW_TZ)


def get_planning_deadline(week_start: date) -> datetime:
  """Момент закрытия приёма пожеланий — начало недели"""
  return datetime.combine(week_start, time(0, 0), tzinfo=MOSCOW_TZ)


def is_planning_open(week_start: date) -> bool:
  """Можно ли сейчас выбирать смены на неделю: с пятницы 15:00 (или с досрочной рассылки) до конца воскресенья"""
  current = now()
  if current >= get_planning_deadline(week_start):
    return False
  return current >= get_planning_opening(week_start) or is_planning_week_opened(week_start)


def get_last_day_text(week_start: date) -> str:
  return (week_start - timedelta(days=1)).strftime("%d.%m")


def format_wish(shifts: list[str]) -> str:
  return ", ".join(order_and_format_shifts(shifts)) if shifts else "без смен"


def get_planning_text(week_start: date, wish: list[str] | None, intro: str) -> str:
  start, end = get_week_range(week_start)
  text = (f"{intro}\n\n"
          f"✍️ Выберите, пожалуйста, смены, в которые вы сможете выйти на неделе с <b>{start}</b> по <b>{end}</b>, "
          f"и нажмите «Отправить». Если выйти не получится — нажмите «Без смен».\n"
          f"🔁 Изменить выбор можно до конца воскресенья <b>{get_last_day_text(week_start)}</b>.")
  if wish is not None:
    text += f"\n\n📝 Ваш выбор, отправленный руководству: <b>{format_wish(wish)}</b>"
  return text


def get_planning_keyboard(week_start: date, wish: list[str] | None) -> InlineKeyboardMarkup:
  return get_shifts_keyboard(week_start, wish, submitted=wish is not None)


async def send_planning_to_coffeemakers(bot: Bot, week_start: date, intro: str):
  """
  Рассылает бариста, которые ещё не отправили выбор на неделю, сообщение с выбором смен.
  Возвращает имена получивших, не получивших сообщение и уже сделавших выбор.
  """
  sent: list[str] = []
  failed: list[str] = []
  skipped: list[str] = []
  for user in get_users():
    if user.is_coffeemaker != 1:
      continue
    if get_shift_wish(week_start, user.id) is not None:
      skipped.append(get_user_name(user))
      continue
    try:
      await bot.send_message(user.id, get_planning_text(week_start, None, intro), parse_mode=ParseMode.HTML,
                             reply_markup=get_planning_keyboard(week_start, None))
      sent.append(get_user_name(user))
    except Exception as e:
      failed.append(f"{get_user_name(user)}: {e}")
    await asyncio.sleep(DELAY_BETWEEN_MESSAGES)
  return sent, failed, skipped


async def plan_next_week(bot: Bot):
  """
  Открывает приём пожеланий на следующую неделю (досрочно, если вызвано раньше пятницы 15:00)
  и рассылает бариста предложение выбрать смены.
  """
  week_start = get_next_week_start()
  open_planning_week(week_start)
  return await send_planning_to_coffeemakers(bot, week_start, GREETING)


async def send_planning_reminder(bot: Bot):
  """Напоминает бариста, которые ещё не выбрали смены на следующую неделю"""
  week_start = get_next_week_start()
  if not is_planning_open(week_start):
    return
  await send_planning_to_coffeemakers(bot, week_start, REMINDER)


def is_coffeemaker(user: User | None) -> bool:
  return user is not None and user.is_coffeemaker == 1


@router.message(F.text.lower() == MY_SHIFTS_BUTTON.lower())
async def handle_my_shifts(message: Message, state: FSMContext):
  user = get_user(message.from_user.id)
  if not is_coffeemaker(user):
    await message.answer("Раздел доступен только бариста")
    return
  # Кнопка меню прерывает незавершённый ввод (например, кода клиента)
  await state.clear()

  week_start = get_next_week_start()
  if is_planning_open(week_start):
    wish = get_shift_wish(week_start, user.id)
    await message.answer(get_planning_text(week_start, wish, "📅 Планирование смен на следующую неделю"),
                         parse_mode=ParseMode.HTML, reply_markup=get_planning_keyboard(week_start, wish))
    return

  text = (f"📅 Выбрать смены на следующую неделю можно будет с пятницы "
          f"<b>{get_planning_opening(week_start).strftime('%d.%m')}</b> 15:00 до конца воскресенья.")
  current_week = get_week_start(today())
  current_wish = get_shift_wish(current_week, user.id)
  if current_wish is not None:
    start, end = get_week_range(current_week)
    text += f"\n\n📝 Ваши пожелания на текущую неделю с {start} по {end}: <b>{format_wish(current_wish)}</b>"
  await message.answer(text, parse_mode=ParseMode.HTML)


async def edit_planning_message(message: Message, text: str | None, reply_markup: InlineKeyboardMarkup | None):
  # Повторное нажатие не меняет сообщение — Telegram отвечает ошибкой, её можно игнорировать
  try:
    if text is None:
      await message.edit_reply_markup(reply_markup=reply_markup)
    else:
      await message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
  except TelegramBadRequest:
    pass


@router.callback_query(ShiftCallback.filter())
async def handle_shift_callback(query: CallbackQuery, callback_data: ShiftCallback, bot: Bot):
  if not isinstance(query.message, Message):
    await query.answer(f"Сообщение устарело. Нажмите «{MY_SHIFTS_BUTTON}» в меню", show_alert=True)
    return
  user = get_user(query.from_user.id)
  if not is_coffeemaker(user):
    await query.answer("Выбирать смены могут только бариста", show_alert=True)
    return
  try:
    week_start = date.fromisoformat(callback_data.week)
  except ValueError:
    await query.answer(f"Сообщение устарело. Нажмите «{MY_SHIFTS_BUTTON}» в меню", show_alert=True)
    return
  if not is_planning_open(week_start):
    await query.answer("⛔ Приём пожеланий на эту неделю закрыт", show_alert=True)
    await edit_planning_message(query.message, None, None)  # Убираем кнопки
    return

  wish = get_shift_wish(week_start, user.id)
  # Отмеченные, но ещё не отправленные смены видны только по галочкам на кнопках
  selected = get_selected_shifts(query.message.reply_markup)
  action = callback_data.action

  if action in ALL_SHIFTS:
    if action in selected:
      selected.remove(action)
    else:
      selected.append(action)
    await edit_planning_message(query.message, None, get_shifts_keyboard(week_start, selected, submitted=wish is not None))
    await query.answer()
    return

  if action == NO_SHIFTS_ACTION:
    shifts = []
  elif action == SUBMIT_ACTION:
    if not selected:
      await query.answer("Вы не выбрали смены ❌\nЕсли не сможете выйти на неделе, нажмите «Без смен»", show_alert=True)
      return
    shifts = sort_shifts(selected)
  else:
    await query.answer()
    return

  if wish is not None and sort_shifts(wish) == shifts:
    await edit_planning_message(query.message, None, get_planning_keyboard(week_start, wish))
    await query.answer("Этот выбор уже отправлен руководству 👌", show_alert=True)
    return

  previous = save_shift_wish(week_start, user.id, shifts)
  await edit_planning_message(query.message, get_planning_text(week_start, shifts, "✅ Ваш выбор отправлен руководству!"),
                              get_planning_keyboard(week_start, shifts))
  await query.answer("✅ Отправлено")

  start, end = get_week_range(week_start, "")
  shifts_text = "\n".join(f"- {s}" for s in order_and_format_shifts(shifts))
  if previous is None:
    action_text = f"выбрал смены:\n{shifts_text}" if shifts else "отказался от смен на неделе"
  else:
    action_text = f"изменил выбор смен:\n{shifts_text}" if shifts else "изменил выбор: без смен"
    action_text += f"\n\nБыло: {format_wish(previous)}"
  await notify_admin_and_managers(bot, f"#planner #week_{start}_{end}\nБариста {get_user_name(user)} {action_text}")


@router.callback_query(F.data.startswith("shift_"))
async def handle_outdated_shift_callback(query: CallbackQuery):
  # Кнопки из сообщений, отправленных до появления сохранения выбора в БД
  await query.answer(f"Сообщение устарело. Нажмите «{MY_SHIFTS_BUTTON}» в меню, чтобы выбрать смены", show_alert=True)


def get_short_name(user: User | None, user_id: int) -> str:
  if user is None:
    return str(user_id)
  return user.name or user.tg_name or (f"@{user.username}" if user.username else str(user_id))


def get_default_wishes_week() -> date:
  """Неделя, которую показывать администраторам: следующая, если по ней уже идёт приём, иначе текущая"""
  next_week = get_next_week_start()
  if is_planning_open(next_week) or get_shift_wishes(next_week):
    return next_week
  return get_week_start(today())


def get_shift_wishes_text(week_start: date) -> str:
  """Сводка пожеланий бариста на неделю для администраторов"""
  start, end = get_week_range(week_start)
  text = f"🗓 <b>Пожелания бариста на неделю {start} – {end}</b>\n"

  if is_planning_open(week_start):
    text += f"🟢 Приём открыт до конца воскресенья {get_last_day_text(week_start)}\n"
  elif now() < get_planning_opening(week_start):
    text += f"⚪️ Приём ещё не открыт, откроется в пятницу {get_planning_opening(week_start).strftime('%d.%m')} в 15:00\n"
  else:
    text += "🔴 Приём закрыт\n"

  wishes = get_shift_wishes(week_start)
  users = {wish.user_id: get_user(wish.user_id) for wish in wishes}
  wishes.sort(key=lambda wish: get_short_name(users[wish.user_id], wish.user_id).lower())

  text += "\n<b>По бариста:</b>\n"
  if not wishes:
    text += "Пока никто не отправил пожелания\n"
  for wish in wishes:
    user = users[wish.user_id]
    name = html.escape(get_user_name(user) if user else str(wish.user_id))
    updated_at = datetime.strptime(wish.updated_at, "%Y-%m-%d %H:%M:%S").strftime("%d.%m %H:%M")
    text += f"☕ {name}: <b>{format_wish(wish.shifts)}</b> <i>({updated_at})</i>\n"

  # Ждём ответа только от действующих бариста и только пока по неделе не закрыт приём
  if now() < get_planning_deadline(week_start):
    answered = {wish.user_id for wish in wishes}
    waiting = [user for user in get_users() if is_coffeemaker(user) and int(user.id) not in answered]
    if waiting:
      text += "\n⏳ <b>Ещё не ответили:</b> " + ", ".join(html.escape(get_user_name(user)) for user in waiting) + "\n"

  if wishes:
    text += "\n<b>По сменам:</b>\n"
    for shift in ALL_SHIFTS:
      names = [html.escape(get_short_name(users[wish.user_id], wish.user_id)) for wish in wishes if shift in wish.shifts]
      text += f"{format_shift(shift)}: {', '.join(names) if names else '—'}\n"
  return text
