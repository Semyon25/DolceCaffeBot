import logging
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, InlineKeyboardMarkup
from utils.admin import get_admin_ids, is_main_admin, main_admin_id

async def notify_admin(bot, message: str, actor_id: int | None = None, **kwargs):
  """
  Отправляет готовое сообщение всем администраторам.
  actor_id — кто выполнил действие: действия главного администратора видит только он сам.
  """
  admin_ids = [main_admin_id] if actor_id is not None and is_main_admin(actor_id) else get_admin_ids()
  for admin_id in admin_ids:
    # Если один администратор заблокировал бота, остальные всё равно должны получить сообщение
    try:
      await bot.send_message(admin_id, message, **kwargs)
    except Exception:
      logging.exception("Не удалось отправить сообщение администратору %s", admin_id)

async def notify_main_admin(bot, message: str, **kwargs):
  """
  Отправляет сообщение только главному администратору.
  """
  try:
    await bot.send_message(main_admin_id, message, **kwargs)
  except Exception:
    logging.exception("Не удалось отправить сообщение главному администратору %s", main_admin_id)

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
