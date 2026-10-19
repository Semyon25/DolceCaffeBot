import asyncio
import html
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from aiogram import Bot, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from bot.planner import (DELAY_BETWEEN_MESSAGES, get_default_wishes_week, get_planning_status, get_schedule_lines,
                         get_schedule_text, get_user_shifts, format_user_shifts)
from db.shift_schedule import (PublishedWeek, get_published_week, get_published_schedule, get_schedule_drafts,
                               set_schedule_draft, remove_schedule_draft, clear_schedule_drafts, publish_schedule)
from db.shift_wishes import get_shift_wishes
from db.users import get_user, get_users
from keyboards.schedule_keyboard import (NOBODY, RESET, PUBLISH_ACTION, CONFIRM_PUBLISH_ACTION, DISCARD_ACTION,
                                         ScheduleWeek, ScheduleShift, ScheduleAssign, ScheduleAction,
                                         get_schedule_editor_keyboard, get_shift_picker_keyboard, get_publish_confirm_keyboard)
from utils.admin import is_admin
from utils.date_utils import today, get_week_range
from utils.send_message import notify_admin_and_managers, edit_message
from utils.shifts import ALL_SHIFTS, format_shift, get_shift_date
from utils.user_utils import get_short_name, get_user_name, is_coffeemaker

router = Router()


def from_admin(event: Message | CallbackQuery) -> bool:
  return is_admin(event.from_user.id)


# Расписание составляют только администраторы
router.message.filter(from_admin)
router.callback_query.filter(from_admin)


@dataclass
class ShiftPlan:
  shift: str
  user_id: int | None  # Кто стоит на смене с учётом неопубликованных правок
  default_user_id: int | None  # Кто стоит на смене без правок: по опубликованному расписанию или по пожеланиям
  wishers: list[int]  # Кто выбрал смену
  edited: bool  # Есть неопубликованная правка, отличная от default_user_id
  conflict: bool  # Смену выбрали несколько бариста, а администратор ещё не решил, кого поставить


@dataclass
class WeekPlan:
  week_start: date
  shifts: list[ShiftPlan]
  published: PublishedWeek | None
  drafts: dict[str, int | None]

  @property
  def schedule(self) -> dict[str, int]:
    """Расписание, которое будет опубликовано: смена -> бариста"""
    return {plan.shift: plan.user_id for plan in self.shifts if plan.user_id is not None}

  @property
  def has_changes(self) -> bool:
    """Есть правки опубликованного расписания"""
    return self.published is not None and any(plan.edited for plan in self.shifts)

  @property
  def read_only(self) -> bool:
    """Прошедшие недели не меняются"""
    return self.week_start + timedelta(days=7) <= today()

  def get(self, shift: str) -> ShiftPlan:
    return next(plan for plan in self.shifts if plan.shift == shift)


def get_week_plan(week_start: date) -> WeekPlan:
  """
  Расписание недели в редакторе. Пока расписание не опубликовано, на смену, которую выбрал один бариста,
  он ставится по умолчанию. Смену, которую выбрали несколько бариста, администратор распределяет сам.
  """
  wishes = get_shift_wishes(week_start)
  published = get_published_week(week_start)
  published_schedule = get_published_schedule(week_start) if published else {}
  drafts = get_schedule_drafts(week_start)
  shifts = []
  for shift in ALL_SHIFTS:
    wishers = [wish.user_id for wish in wishes if shift in wish.shifts]
    if published:
      default_user_id = published_schedule.get(shift)
    else:
      default_user_id = wishers[0] if len(wishers) == 1 else None
    user_id = drafts[shift] if shift in drafts else default_user_id
    shifts.append(ShiftPlan(
      shift=shift,
      user_id=user_id,
      default_user_id=default_user_id,
      wishers=wishers,
      edited=shift in drafts and user_id != default_user_id,
      conflict=not published and shift not in drafts and len(wishers) > 1,
    ))
  return WeekPlan(week_start, shifts, published, drafts)


def get_plan_names(plan: WeekPlan) -> dict[int, str]:
  """Короткие имена всех бариста недели (без экранирования HTML)"""
  user_ids = {user_id for shift in plan.shifts for user_id in shift.wishers + [shift.user_id] if user_id is not None}
  return {user_id: get_short_name(get_user(user_id), user_id) for user_id in user_ids}


def format_datetime(value: str) -> str:
  return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").strftime("%d.%m %H:%M")


def get_shift_title(week_start: date, shift: str) -> str:
  """«Пн 26.10 10-16»"""
  day_name, time_name = format_shift(shift).split(" ", 1)
  return f"{day_name} {get_shift_date(week_start, shift):%d.%m} {time_name}"


def get_shift_mark(plan: WeekPlan, shift: ShiftPlan) -> str:
  if shift.conflict:
    return "⚠️ "
  if shift.edited and plan.published is not None:
    return "✏️ "
  return ""


def get_editor_text(plan: WeekPlan) -> str:
  names = {user_id: html.escape(name) for user_id, name in get_plan_names(plan).items()}
  start, end = get_week_range(plan.week_start)
  text = f"📝 <b>Расписание на неделю {start} – {end}</b>\n"
  if plan.published is None:
    text += "Черновик — бариста его ещё не видят\n"
  else:
    text += f"✅ Опубликовано {format_datetime(plan.published.published_at)}"
    if plan.published.updated_at != plan.published.published_at:
      text += f", изменено {format_datetime(plan.published.updated_at)}"
    text += "\n"
    if plan.has_changes:
      text += "✏️ Есть неопубликованные изменения\n"
  text += get_planning_status(plan.week_start) + "\n\n"

  for shift in plan.shifts:
    name = names[shift.user_id] if shift.user_id is not None else "—"
    line = f"{format_shift(shift.shift)}: {get_shift_mark(plan, shift)}<b>{name}</b>"
    if shift.wishers:
      line += " · 🙋 " + ", ".join(names[user_id] for user_id in shift.wishers)
    text += line + "\n"

  text += "\n🙋 — выбрали смену"
  if any(shift.conflict for shift in plan.shifts):
    text += "\n⚠️ — смену выбрали несколько бариста, назначьте сами"
  if plan.has_changes:
    text += "\n✏️ — изменено, но не опубликовано"
  if plan.read_only:
    text += "\n\n🔒 Неделя прошла, расписание нельзя изменить"
  else:
    text += "\n\nНажмите на смену, чтобы назначить бариста ⬇"
  return text


def get_editor_keyboard(plan: WeekPlan):
  names = get_plan_names(plan)
  shift_buttons = [(shift.shift, f"{get_shift_mark(plan, shift)}{format_shift(shift.shift)} "
                                 f"{names[shift.user_id] if shift.user_id is not None else '—'}")
                   for shift in plan.shifts]
  if plan.published is None:
    publish_text = "📢 Опубликовать"
  elif plan.has_changes:
    publish_text = "📢 Опубликовать изменения"
  else:
    publish_text = None
  discard_text = None
  if plan.drafts:
    discard_text = "↩️ Отменить изменения" if plan.published else "↩️ Сбросить черновик"
  return get_schedule_editor_keyboard(plan.week_start, shift_buttons, plan.read_only, publish_text, discard_text)


async def send_schedule_editor(message: Message, week_start: date | None = None):
  """Присылает редактор расписания. По умолчанию — на неделю, по которой идёт планирование."""
  plan = get_week_plan(week_start or get_default_wishes_week())
  await message.answer(get_editor_text(plan), parse_mode=ParseMode.HTML, reply_markup=get_editor_keyboard(plan))


async def show_editor(query: CallbackQuery, plan: WeekPlan):
  await edit_message(query.message, get_editor_text(plan), get_editor_keyboard(plan))


@router.message(Command('schedule'))
async def schedule_handler(message: Message):
  await send_schedule_editor(message)


def parse_week(week: str) -> date | None:
  try:
    return date.fromisoformat(week)
  except ValueError:
    return None


async def get_editable_plan(query: CallbackQuery, week: str, shift: str | None = None) -> WeekPlan | None:
  """Расписание недели для правки. Если неделю менять нельзя, отвечает администратору и возвращает None."""
  week_start = parse_week(week)
  if week_start is None or (shift is not None and shift not in ALL_SHIFTS):
    await query.answer("Действие устарело. Откройте расписание заново: /schedule", show_alert=True)
    return None
  plan = get_week_plan(week_start)
  if plan.read_only:
    await query.answer("🔒 Неделя прошла, расписание нельзя изменить", show_alert=True)
    await show_editor(query, plan)
    return None
  return plan


@router.callback_query(ScheduleWeek.filter())
async def handle_schedule_week(query: CallbackQuery, callback_data: ScheduleWeek):
  week_start = parse_week(callback_data.week)
  if week_start is None:
    await query.answer("Действие устарело. Откройте расписание заново: /schedule", show_alert=True)
    return
  await show_editor(query, get_week_plan(week_start))
  await query.answer()


def get_shift_count(plan: WeekPlan, user_id: int) -> int:
  return sum(1 for shift in plan.shifts if shift.user_id == user_id)


async def show_shift_picker(query: CallbackQuery, plan: WeekPlan, shift_code: str):
  shift = plan.get(shift_code)
  names = get_plan_names(plan)
  coffeemakers = {int(user.id): get_short_name(user, int(user.id)) for user in get_users() if is_coffeemaker(user)}
  names.update(coffeemakers)

  # Сначала те, кто выбрал смену, затем остальные бариста; назначенный, но уже не бариста, тоже в списке
  others = [user_id for user_id in coffeemakers if user_id not in shift.wishers]
  if shift.user_id is not None and shift.user_id not in shift.wishers and shift.user_id not in others:
    others.append(shift.user_id)
  by_name = lambda user_id: names[user_id].lower()
  candidates = []
  for user_id in sorted(shift.wishers, key=by_name) + sorted(others, key=by_name):
    text = ("✅ " if user_id == shift.user_id else "") + names[user_id]
    if user_id in shift.wishers:
      text += " 🙋"
    count = get_shift_count(plan, user_id)
    if count:
      text += f" · смен: {count}"
    candidates.append((user_id, text))

  start, end = get_week_range(plan.week_start)
  current = html.escape(names[shift.user_id]) if shift.user_id is not None else "никого"
  text = f"📝 Расписание на неделю {start} – {end}\n\n<b>{get_shift_title(plan.week_start, shift.shift)}</b>\n"
  text += f"Сейчас: <b>{current}</b>" + (" ✏️ (не опубликовано)" if shift.edited and plan.published else "") + "\n"
  if shift.wishers:
    text += "🙋 Выбрали смену: " + ", ".join(html.escape(names[user_id]) for user_id in shift.wishers) + "\n"
  else:
    text += "🙋 Эту смену никто не выбрал\n"
  text += "\nКого поставить на смену? ⬇"
  await edit_message(query.message, text, get_shift_picker_keyboard(plan.week_start, shift.shift, candidates,
                                                                     nobody_selected=shift.user_id is None,
                                                                     can_reset=shift.shift in plan.drafts))


@router.callback_query(ScheduleShift.filter())
async def handle_schedule_shift(query: CallbackQuery, callback_data: ScheduleShift):
  plan = await get_editable_plan(query, callback_data.week, callback_data.shift)
  if plan is None:
    return
  await show_shift_picker(query, plan, callback_data.shift)
  await query.answer()


@router.callback_query(ScheduleAssign.filter())
async def handle_schedule_assign(query: CallbackQuery, callback_data: ScheduleAssign):
  plan = await get_editable_plan(query, callback_data.week, callback_data.shift)
  if plan is None:
    return
  shift = plan.get(callback_data.shift)
  if callback_data.user_id == RESET:
    remove_schedule_draft(plan.week_start, shift.shift)
  else:
    user_id = None if callback_data.user_id == NOBODY else callback_data.user_id
    if user_id is not None and get_user(user_id) is None:
      await query.answer("❌ Такого пользователя нет в боте", show_alert=True)
      return
    # Правка, совпадающая с опубликованным расписанием, не нужна. До публикации правка хранится всегда:
    # она означает, что администратор уже решил, кого поставить на смену
    if plan.published is not None and user_id == shift.default_user_id:
      remove_schedule_draft(plan.week_start, shift.shift)
    else:
      set_schedule_draft(plan.week_start, shift.shift, user_id)
  await show_editor(query, get_week_plan(plan.week_start))
  await query.answer()


def get_changes_text(previous: dict[str, int], schedule: dict[str, int], week_start: date, names: dict[int, str]) -> str:
  """Изменённые смены (HTML): «Пн 26.10 10-16: Аня → Боря»"""
  lines = []
  for shift in ALL_SHIFTS:
    old, new = previous.get(shift), schedule.get(shift)
    if old != new:
      old_name = html.escape(names[old]) if old is not None else "—"
      new_name = html.escape(names[new]) if new is not None else "—"
      lines.append(f"{get_shift_title(week_start, shift)}: {old_name} → {new_name}")
  return "\n".join(lines)


@router.callback_query(ScheduleAction.filter())
async def handle_schedule_action(query: CallbackQuery, callback_data: ScheduleAction, bot: Bot):
  plan = await get_editable_plan(query, callback_data.week)
  if plan is None:
    return
  action = callback_data.action

  if action == DISCARD_ACTION:
    clear_schedule_drafts(plan.week_start)
    await show_editor(query, get_week_plan(plan.week_start))
    await query.answer("Правки отменены")
    return

  if action not in (PUBLISH_ACTION, CONFIRM_PUBLISH_ACTION):
    await query.answer()
    return
  if plan.published is not None and not plan.has_changes:
    await query.answer("Нет изменений для публикации", show_alert=True)
    await show_editor(query, plan)
    return

  if action == PUBLISH_ACTION:
    await show_publish_confirm(query, plan)
    await query.answer()
    return

  await query.answer()
  previous = get_published_schedule(plan.week_start) if plan.published else None
  schedule = plan.schedule
  publish_schedule(plan.week_start, schedule)
  await show_editor(query, get_week_plan(plan.week_start))
  await notify_about_schedule(query.message, bot, plan.week_start, schedule, previous)


async def show_publish_confirm(query: CallbackQuery, plan: WeekPlan):
  start, end = get_week_range(plan.week_start)
  schedule = plan.schedule
  if plan.published is None:
    text = (f"📢 <b>Опубликовать расписание на неделю {start} – {end}?</b>\n\n"
            f"Все бариста получат расписание, выбор смен на эту неделю закроется.\n\n"
            f"{get_schedule_lines(schedule)}")
  else:
    names = get_plan_names(plan)
    names.update({user_id: get_short_name(get_user(user_id), user_id) for user_id in get_published_schedule(plan.week_start).values()})
    text = (f"📢 <b>Опубликовать изменения расписания на неделю {start} – {end}?</b>\n\n"
            f"Бариста, у которых изменились смены, получат уведомление.\n\n"
            f"<b>Изменения:</b>\n{get_changes_text(get_published_schedule(plan.week_start), schedule, plan.week_start, names)}")
  empty = [shift for shift in plan.shifts if shift.user_id is None]
  if empty:
    text += "\n\n⚠️ Смены без бариста: " + ", ".join(format_shift(shift.shift) for shift in empty)
    conflicts = [shift for shift in empty if shift.conflict]
    if conflicts:
      text += "\nИз них выбрали несколько бариста: " + ", ".join(format_shift(shift.shift) for shift in conflicts)
  await edit_message(query.message, text, get_publish_confirm_keyboard(plan.week_start))


async def notify_about_schedule(message: Message, bot: Bot, week_start: date, schedule: dict[str, int],
                                previous: dict[str, int] | None):
  """
  Рассылает опубликованное расписание: при первой публикации — всем бариста, при изменении — тем,
  у кого изменились смены. Администраторам и менеджерам приходит расписание, администратору — отчёт о рассылке.
  """
  start, end = get_week_range(week_start)
  if previous is None:
    recipients = {int(user.id) for user in get_users() if is_coffeemaker(user)} | set(schedule.values())
  else:
    recipients = {user_id for user_id in set(schedule.values()) | set(previous.values())
                  if get_user_shifts(schedule, user_id) != get_user_shifts(previous, user_id)}

  sent: list[str] = []
  failed: list[str] = []
  for user_id in sorted(recipients):
    user = get_user(user_id)
    if previous is None:
      text = get_schedule_text(week_start, schedule, user_id, "📅 Расписание на неделю")
    else:
      text = (f"✏️ <b>Расписание на неделю {start} – {end} изменилось</b>\n\n"
              f"Ваши смены: <b>{format_user_shifts(get_user_shifts(schedule, user_id))}</b>\n"
              f"Было: {format_user_shifts(get_user_shifts(previous, user_id))}\n\n"
              f"{get_schedule_lines(schedule, user_id)}")
    try:
      await bot.send_message(user_id, text, parse_mode=ParseMode.HTML)
      sent.append(get_user_name(user) or str(user_id))
    except Exception as e:
      failed.append(f"{get_user_name(user) or user_id}: {e}")
    await asyncio.sleep(DELAY_BETWEEN_MESSAGES)

  hashtag_start, hashtag_end = get_week_range(week_start, "")
  hashtags = f"#schedule #week_{hashtag_start}_{hashtag_end}"
  if previous is None:
    admin_text = f"{hashtags}\n📅 <b>Опубликовано расписание на неделю {start} – {end}</b>\n\n{get_schedule_lines(schedule)}"
  else:
    names = {user_id: get_short_name(get_user(user_id), user_id) for user_id in set(schedule.values()) | set(previous.values())}
    admin_text = (f"{hashtags}\n✏️ <b>Изменено расписание на неделю {start} – {end}</b>\n\n"
                  f"{get_changes_text(previous, schedule, week_start, names)}\n\n{get_schedule_lines(schedule)}")
  await notify_admin_and_managers(bot, admin_text, parse_mode=ParseMode.HTML)

  report = f"✅ Расписание опубликовано. Уведомление получили бариста: {len(sent)}"
  if sent:
    report += "\n" + "\n".join(f"- {name}" for name in sent)
  if failed:
    report += f"\n\n❌ Не удалось отправить: {len(failed)}\n" + "\n".join(f"- {error}" for error in failed)
  await message.answer(report)
