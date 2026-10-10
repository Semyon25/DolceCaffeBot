from datetime import date, timedelta
from aiogram import Bot
from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import config
from db.users import get_user
from utils.admin import is_admin
from utils.date_utils import today
from utils.send_message import notify_admin
from utils.user_utils import get_user_name

router = Router()

# Срок, на который продлевается оплата после нажатия «Я оплатил»
PAYMENT_PERIOD_DAYS = 30
# За сколько дней до оплаты напоминать (0 — в день оплаты)
REMIND_DAYS_BEFORE = (3, 1, 0)
PAID_CALLBACK_PREFIX = "payment_paid_"


def format_date(d: date) -> str:
  return d.strftime(config.PAYMENT_DATE_FORMAT)


def get_payment_keyboard(due_date: date) -> InlineKeyboardMarkup:
  # В кнопку зашита дата оплаты, чтобы повторное нажатие не продлило оплату дважды
  return InlineKeyboardMarkup(inline_keyboard=[[
      InlineKeyboardButton(text="✅ Я оплатил",
                           callback_data=f"{PAID_CALLBACK_PREFIX}{due_date.isoformat()}")
  ]])


async def send_payment_reminder(bot: Bot):
  """
  Напоминает администраторам об оплате размещения бота за 3 дня, за 1 день и в день оплаты.
  """
  due_date = config.payment_date
  if due_date is None:
    return
  days_left = (due_date - today()).days
  if days_left not in REMIND_DAYS_BEFORE:
    return

  if days_left == 0:
    when = f"<b>Сегодня, {format_date(due_date)}</b>,"
  elif days_left == 1:
    when = f"<b>Завтра, {format_date(due_date)}</b>,"
  else:
    when = f"<b>Через {days_left} дня, {format_date(due_date)}</b>,"

  text = (f"#payment\n💳 {when} необходимо оплатить размещение бота.\n\n"
          "После оплаты нажмите кнопку <b>«Я оплатил»</b> ✅")

  await notify_admin(bot, text, parse_mode=ParseMode.HTML,
                     reply_markup=get_payment_keyboard(due_date))


@router.callback_query(F.data.startswith(PAID_CALLBACK_PREFIX))
async def handle_payment_paid(query: CallbackQuery, bot: Bot):
  if not is_admin(query.from_user.id):
    await query.answer()
    return

  paid_date = date.fromisoformat(query.data.removeprefix(PAID_CALLBACK_PREFIX))
  await query.message.edit_reply_markup(reply_markup=None)

  # Оплату за эту дату уже отметил другой администратор
  if config.payment_date != paid_date:
    await query.answer("Оплата уже отмечена ✅", show_alert=True)
    return

  # Новый период отсчитывается от даты оплаты, а если оплата сильно просрочена — от сегодняшнего дня
  next_date = paid_date + timedelta(days=PAYMENT_PERIOD_DAYS)
  if next_date <= today():
    next_date = today() + timedelta(days=PAYMENT_PERIOD_DAYS)
  config.save_payment_date(next_date)

  await query.answer("Спасибо! Оплата отмечена ✅")
  admin = get_user(query.from_user.id)
  admin_name = get_user_name(admin).strip() or str(query.from_user.id)
  await notify_admin(bot,
                     f"#payment\n✅ {admin_name} отметил оплату размещения бота за {format_date(paid_date)}.\n"
                     f"Следующая оплата: <b>{format_date(next_date)}</b>",
                     parse_mode=ParseMode.HTML)
