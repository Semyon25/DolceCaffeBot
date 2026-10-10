import logging
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

async def notify_admin_and_managers(bot, message: str):
  """
  Отправляет готовое сообщение администраторам и менеджерам.
  """
  # Отправка администраторам
  await notify_admin(bot, message)

  # Отправка менеджерам (кроме тех, кто уже получил сообщение как администратор)
  for manager_id in get_manager_ids():
    if manager_id not in get_admin_ids():
      await bot.send_message(manager_id, message)
