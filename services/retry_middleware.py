import asyncio
import logging
from aiogram import Bot
from aiogram.client.session.middlewares.base import BaseRequestMiddleware, NextRequestMiddlewareType
from aiogram.exceptions import TelegramNetworkError
from aiogram.methods import GetUpdates, Response, TelegramMethod
from aiogram.methods.base import TelegramType


class RetryRequestMiddleware(BaseRequestMiddleware):
  """
  Повторяет запрос к Telegram при сетевых ошибках (например, Connection reset by peer),
  чтобы кратковременный обрыв соединения не приводил к потере ответа пользователю.
  """

  def __init__(self, attempts: int = 3, delay: float = 1):
    self.attempts = attempts
    self.delay = delay

  async def __call__(self,
                     make_request: NextRequestMiddlewareType[TelegramType],
                     bot: Bot,
                     method: TelegramMethod[TelegramType]) -> Response[TelegramType]:
    # Получение обновлений aiogram сам повторяет при ошибках
    if isinstance(method, GetUpdates):
      return await make_request(bot, method)

    for attempt in range(1, self.attempts + 1):
      try:
        return await make_request(bot, method)
      except TelegramNetworkError as e:
        if attempt == self.attempts:
          raise
        logging.warning("Сетевая ошибка при запросе %s (попытка %s из %s): %s",
                        type(method).__name__, attempt, self.attempts, e)
        await asyncio.sleep(self.delay * attempt)
