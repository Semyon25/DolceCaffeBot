from utils.admin import get_admin_id, get_manager_ids

async def notify_admin(bot, message: str):
  """
  Отправляет готовое сообщение администратору.
  """
  admin_id = get_admin_id()
  await bot.send_message(admin_id, message)

async def notify_admin_and_managers(bot, message: str):
  """
  Отправляет готовое сообщение администратору и менеджерам.
  """
  # Отправка администратору
  await notify_admin(bot, message)

  # Отправка менеджерам
  for manager_id in get_manager_ids():
      await bot.send_message(manager_id, message)