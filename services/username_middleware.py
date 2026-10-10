import logging
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from db.users import update_username


class UsernameMiddleware(BaseMiddleware):
  """
  Обновляет username пользователя в базе при любом взаимодействии с ботом.
  Чтобы не ходить в базу на каждое сообщение, последние известные username хранятся в памяти.
  """

  def __init__(self):
    self.known_usernames: Dict[int, str | None] = {}

  async def __call__(self,
                     handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
                     event: TelegramObject,
                     data: Dict[str, Any]) -> Any:
    user: User | None = data.get("event_from_user")
    if user is not None and not user.is_bot:
      # Пользователя ещё нет в кэше или username изменился
      if user.id not in self.known_usernames or self.known_usernames[user.id] != user.username:
        try:
          # Если пользователя нет в базе (ещё не нажал /start), не кэшируем — его создаст /start
          if update_username(user.id, user.username):
            self.known_usernames[user.id] = user.username
        except Exception:
          # Ошибка обновления username не должна мешать обработке сообщения
          logging.exception("Не удалось обновить username пользователя %s", user.id)
    return await handler(event, data)
