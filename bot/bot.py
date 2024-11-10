import os
from aiogram import Bot, Dispatcher
from bot import start, feedback_bot, coffeemaker_bot

# Запуск процесса поллинга новых апдейтов
async def main():
  # Включаем логирование, чтобы не пропустить важные сообщения
  # logging.basicConfig(level=logging.INFO)

  bot_token = os.environ['bot_token']
  bot = Bot(token=bot_token)
  dp = Dispatcher()

  dp.include_routers(start.router, feedback_bot.router, coffeemaker_bot.router)
  # Запускаем бота и пропускаем все накопленные входящие
  await bot.delete_webhook(drop_pending_updates=True)
  await dp.start_polling(bot)
