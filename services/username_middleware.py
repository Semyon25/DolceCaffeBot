import logging
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from db.users import update_user_profile


class UsernameMiddleware(BaseMiddleware):
  """
  Обновляет username, имя и фамилию пользователя в базе при любом взаимодействии с ботом.
  Чтобы не ходить в базу на каждое сообщение, последние известные данные хранятся в памяти.
  """

  def __init__(self):
    self.known_profiles: Dict[int, tuple] = {}

  async def __call__(self,
                     handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
                     event: TelegramObject,
                     data: Dict[str, Any]) -> Any:
    user: User | None = data.get("event_from_user")
    if user is not None and not user.is_bot:
      profile = (user.username, user.first_name, user.last_name)
      # Пользователя ещё нет в кэше или его данные изменились
      if self.known_profiles.get(user.id) != profile:
        try:
          # Если пользователя нет в базе (ещё не нажал /start), не кэшируем — его создаст /start
          if update_user_profile(user.id, *profile):
            self.known_profiles[user.id] = profile
        except Exception:
          # Ошибка обновления данных не должна мешать обработке сообщения
          logging.exception("Не удалось обновить данные пользователя %s", user.id)
    return await handler(event, data)
