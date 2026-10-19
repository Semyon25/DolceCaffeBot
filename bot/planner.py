import asyncio
import html
from datetime import date, datetime, time, timedelta
from aiogram import Bot
from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup
from db.shift_schedule import is_schedule_published, get_published_schedule
from db.shift_wishes import open_planning_week, is_planning_week_opened, get_shift_wish, save_shift_wish, get_shift_wishes
from db.users import get_users, get_user
from keyboards.main_menu import MY_SHIFTS_BUTTON
from keyboards.shifts_keyboard import ShiftCallback, NO_SHIFTS_ACTION, SUBMIT_ACTION, get_shifts_keyboard, get_selected_shifts
from utils.date_utils import MOSCOW_TZ, now, today, get_week_start, get_next_week_start, get_week_range
from utils.user_utils import get_user_name, get_short_name, is_coffeemaker
from utils.shifts import ALL_SHIFTS, DAYS, DAY_ORDER, TIMES, TIME_ORDER, format_shift, sort_shifts, order_and_format_shifts
from utils.send_message import notify_admin_and_managers, edit_message

router = Router()

# Задержка между отправками сообщений в секундах (чтобы не превысить лимиты Telegram)
DELAY_BETWEEN_MESSAGES = 1

# Приём пожеланий на неделю открывается в пятницу перед ней в 15:00 и длится до конца воскресенья
OPENING_DAYS_BEFORE_WEEK = 3
OPENING_TIME = time(15, 0)

GREETING = "👋 Добрый день!\n\n📅 Давайте запланируем ваш график на следующую неделю."
REMINDER = "⏰ Напоминаем: вы ещё не выбрали смены на следующую неделю."
OUTDATED_TEXT = f"Сообщение устарело. Нажмите «{MY_SHIFTS_BUTTON}» в меню"


def get_planning_opening(week_start: date) -> datetime:
  return datetime.combine(week_start - timedelta(days=OPENING_DAYS_BEFORE_WEEK), OPENING_TIME, tzinfo=MOSCOW_TZ)


def get_planning_deadline(week_start: date) -> datetime:
  """Момент закрытия приёма пожеланий — начало недели"""
  return datetime.combine(week_start, time(0, 0), tzinfo=MOSCOW_TZ)


def is_planning_open(week_start: date) -> bool:
  """
  Можно ли сейчас выбирать смены на неделю: с пятницы 15:00 (или с досрочной рассылки) до конца воскресенья.
  После публикации расписания на неделю выбор закрывается.
  """
  current = now()
  if current >= get_planning_deadline(week_start) or is_schedule_published(week_start):
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


def get_names(user_ids) -> dict[int, str]:
  """Короткие имена бариста для расписания (HTML)"""
  return {user_id: html.escape(get_short_name(get_user(user_id), user_id)) for user_id in set(user_ids)}


def get_schedule_lines(schedule: dict[str, int], viewer_id: int | None = None) -> str:
  """Расписание недели по дням (HTML): «Пн: 10-16 Аня, 16-22 Боря». Имя viewer_id выделено жирным."""
  names = get_names(schedule.values())
  lines = []
  for day in DAYS:
    parts = []
    for shift_time in TIMES:
      user_id = schedule.get(f"{day}_{shift_time}")
      if user_id is None:
        name = "—"
      elif user_id == viewer_id:
        name = f"<b>{names[user_id]}</b>"
      else:
        name = names[user_id]
      parts.append(f"{TIME_ORDER[shift_time][1]} {name}")
    lines.append(f"{DAY_ORDER[day][1]}: " + ", ".join(parts))
  return "\n".join(lines)


def get_user_shifts(schedule: dict[str, int], user_id: int) -> list[str]:
  return sort_shifts([shift for shift, assigned in schedule.items() if assigned == user_id])


def format_user_shifts(shifts: list[str]) -> str:
  return ", ".join(order_and_format_shifts(shifts)) if shifts else "нет смен"


def get_schedule_text(week_start: date, schedule: dict[str, int], viewer_id: int, title: str) -> str:
  """Расписание недели для бариста с его сменами"""
  start, end = get_week_range(week_start)
  text = f"{title} <b>{start} – {end}</b>\n\n{get_schedule_lines(schedule, viewer_id)}\n\n"
  shifts = get_user_shifts(schedule, viewer_id)
  text += f"✅ Ваши смены: <b>{format_user_shifts(shifts)}</b>" if shifts else "🙅 На этой неделе у вас нет смен"
  return text


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
  и рассылает бариста предложение выбрать смены. Если расписание уже опубликовано, ничего не делает.
  """
  week_start = get_next_week_start()
  if is_schedule_published(week_start):
    return [], [], []
  open_planning_week(week_start)
  return await send_planning_to_coffeemakers(bot, week_start, GREETING)


async def send_planning_reminder(bot: Bot):
  """Напоминает бариста, которые ещё не выбрали смены на следующую неделю"""
  week_start = get_next_week_start()
  if not is_planning_open(week_start):
    return
  await send_planning_to_coffeemakers(bot, week_start, REMINDER)


@router.message(F.text.lower() == MY_SHIFTS_BUTTON.lower())
async def handle_my_shifts(message: Message, state: FSMContext):
  user = get_user(message.from_user.id)
  if not is_coffeemaker(user):
    await message.answer("Раздел доступен только бариста")
    return
  # Кнопка меню прерывает незавершённый ввод (например, кода клиента)
  await state.clear()
  user_id = int(user.id)

  current_week = get_week_start(today())
  current_published = is_schedule_published(current_week)
  if current_published:
    await message.answer(get_schedule_text(current_week, get_published_schedule(current_week), user_id,
                                           "📅 Расписание на текущую неделю"), parse_mode=ParseMode.HTML)

  next_week = get_next_week_start()
  if is_schedule_published(next_week):
    await message.answer(get_schedule_text(next_week, get_published_schedule(next_week), user_id,
                                           "📅 Расписание на следующую неделю"), parse_mode=ParseMode.HTML)
    return
  if is_planning_open(next_week):
    wish = get_shift_wish(next_week, user_id)
    await message.answer(get_planning_text(next_week, wish, "📅 Планирование смен на следующую неделю"),
                         parse_mode=ParseMode.HTML, reply_markup=get_planning_keyboard(next_week, wish))
    return

  text = (f"📅 Выбрать смены на следующую неделю можно будет с пятницы "
          f"<b>{get_planning_opening(next_week).strftime('%d.%m')}</b> 15:00 до конца воскресенья.")
  if not current_published:
    current_wish = get_shift_wish(current_week, user_id)
    if current_wish is not None:
      start, end = get_week_range(current_week)
      text += f"\n\n📝 Ваши пожелания на текущую неделю с {start} по {end}: <b>{format_wish(current_wish)}</b>"
  await message.answer(text, parse_mode=ParseMode.HTML)


@router.callback_query(ShiftCallback.filter())
async def handle_shift_callback(query: CallbackQuery, callback_data: ShiftCallback, bot: Bot):
  if not isinstance(query.message, Message):
    await query.answer(OUTDATED_TEXT, show_alert=True)
    return
  user = get_user(query.from_user.id)
  if not is_coffeemaker(user):
    await query.answer("Выбирать смены могут только бариста", show_alert=True)
    return
  try:
    week_start = date.fromisoformat(callback_data.week)
  except ValueError:
    await query.answer(OUTDATED_TEXT, show_alert=True)
    return
  if not is_planning_open(week_start):
    if is_schedule_published(week_start):
      await query.answer(f"📅 Расписание на эту неделю уже составлено. Нажмите «{MY_SHIFTS_BUTTON}» в меню, чтобы посмотреть его",
                         show_alert=True)
    else:
      await query.answer("⛔ Приём пожеланий на эту неделю закрыт", show_alert=True)
    await edit_message(query.message, None, None)  # Убираем кнопки
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
    await edit_message(query.message, None, get_shifts_keyboard(week_start, selected, submitted=wish is not None))
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
    await edit_message(query.message, None, get_planning_keyboard(week_start, wish))
    await query.answer("Этот выбор уже отправлен руководству 👌", show_alert=True)
    return

  previous = save_shift_wish(week_start, user.id, shifts)
  await edit_message(query.message, get_planning_text(week_start, shifts, "✅ Ваш выбор отправлен руководству!"),
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
  await query.answer(f"{OUTDATED_TEXT}, чтобы выбрать смены", show_alert=True)


def get_default_wishes_week() -> date:
  """Неделя, которую показывать администраторам: следующая, если по ней уже идёт приём, иначе текущая"""
  next_week = get_next_week_start()
  if is_planning_open(next_week) or get_shift_wishes(next_week) or is_schedule_published(next_week):
    return next_week
  return get_week_start(today())


def get_planning_status(week_start: date) -> str:
  """Состояние приёма пожеланий на неделю для администраторов"""
  if is_planning_open(week_start):
    return f"🟢 Приём пожеланий открыт до конца воскресенья {get_last_day_text(week_start)}"
  if is_schedule_published(week_start):
    return "🔒 Расписание опубликовано, приём пожеланий закрыт"
  if now() < get_planning_opening(week_start):
    return f"⚪️ Приём пожеланий ещё не открыт, откроется в пятницу {get_planning_opening(week_start).strftime('%d.%m')} в 15:00"
  return "🔴 Приём пожеланий закрыт"


def get_shift_wishes_text(week_start: date) -> str:
  """Сводка пожеланий бариста на неделю для администраторов"""
  start, end = get_week_range(week_start)
  text = f"🗓 <b>Пожелания бариста на неделю {start} – {end}</b>\n{get_planning_status(week_start)}\n"

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
  if now() < get_planning_deadline(week_start) and not is_schedule_published(week_start):
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
