import logging
from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import ExceptionMessageFilter, ExceptionTypeFilter
from aiogram.types import ErrorEvent

router = Router()


@router.error(ExceptionTypeFilter(TelegramBadRequest), ExceptionMessageFilter(r".*query is too old"))
async def handle_old_callback_query(event: ErrorEvent):
  """
  Ответ на нажатие кнопки опоздал: Telegram принимает его только в первые секунды после нажатия.
  Так бывает, когда бот обрабатывает накопившиеся нажатия после перезапуска или сетевой задержки.
  Само действие уже выполнено, не хватает только ответа на нажатие, поэтому трейсбек не нужен.
  """
  logging.warning("Ответ на нажатие кнопки опоздал (update %s): %s", event.update.update_id, event.exception)
  return True
