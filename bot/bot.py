import os
from aiogram import Bot, Dispatcher
from bot import start, help, feedback_bot, coffeemaker_bot, anyText_bot, broadcast_bot
import settings.consts

# Запуск процесса поллинга новых апдейтов
async def main():
  # Включаем логирование, чтобы не пропустить важные сообщения
  # logging.basicConfig(level=logging.INFO)

  bot_token = os.environ['bot_token']
  bot = Bot(token=bot_token)
  dp = Dispatcher()
  dp.include_router(start.router)
  dp.include_router(help.router)
  dp.include_router(coffeemaker_bot.router)
  if settings.consts.FEEDBACK_MODE:
    dp.include_router(feedback_bot.router)
  dp.include_router(broadcast_bot.router)
  dp.include_router(anyText_bot.router)
  # Запускаем бота и пропускаем все накопленные входящие
  # await bot.delete_webhook(drop_pending_updates=True)
  await dp.start_polling(bot)
