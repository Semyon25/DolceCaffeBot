import logging
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, InlineKeyboardMarkup
from utils.admin import get_admin_ids, get_manager_ids

async def notify_admin(bot, message: str, **kwargs):
  """
  Отправляет готовое сообщение всем администраторам.
  """
  for admin_id in get_admin_ids():
    # Если один администратор заблокировал бота, остальные всё равно должны получить сообщение
    try:
      await bot.send_message(admin_id, message, **kwargs)
    except Exception:
      logging.exception("Не удалось отправить сообщение администратору %s", admin_id)

async def notify_admin_and_managers(bot, message: str, **kwargs):
  """
  Отправляет готовое сообщение администраторам и менеджерам.
  """
  # Отправка администраторам
  await notify_admin(bot, message, **kwargs)

  # Отправка менеджерам (кроме тех, кто уже получил сообщение как администратор)
  for manager_id in get_manager_ids():
    if manager_id not in get_admin_ids():
      try:
        await bot.send_message(manager_id, message, **kwargs)
      except Exception:
        logging.exception("Не удалось отправить сообщение менеджеру %s", manager_id)

async def edit_message(message: Message, text: str | None, reply_markup: InlineKeyboardMarkup | None):
  """
  Меняет текст (HTML) и кнопки сообщения, а если text не задан — только кнопки.
  """
  # Повторное нажатие не меняет сообщение — Telegram отвечает ошибкой, её можно игнорировать
  try:
    if text is None:
      await message.edit_reply_markup(reply_markup=reply_markup)
    else:
      await message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
  except TelegramBadRequest:
    pass
