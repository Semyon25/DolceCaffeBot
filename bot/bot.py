from config import bot_token
from aiogram import Bot, Dispatcher
from bot import start, help, feedback_bot, coffeemaker_bot, anyText_bot, broadcast_bot, purchase_bot, cashbox_bot, planner
import settings.consts
from services.scheduler import SchedulerService

# Запуск процесса поллинга новых апдейтов
async def main():
  # Включаем логирование, чтобы не пропустить важные сообщения
  # logging.basicConfig(level=logging.INFO)

  bot = Bot(token=bot_token)
  dp = Dispatcher()
  dp.include_router(start.router)
  dp.include_router(help.router)
  dp.include_router(coffeemaker_bot.router)
  dp.include_router(cashbox_bot.router)
  if settings.consts.FEEDBACK_MODE:
    dp.include_router(feedback_bot.router)
  if settings.consts.PURCHASE_MODE:
    dp.include_router(purchase_bot.router)
  dp.include_router(broadcast_bot.router)
  dp.include_router(planner.router)
  dp.include_router(anyText_bot.router)
  # Запускаем бота и пропускаем все накопленные входящие
  # await bot.delete_webhook(drop_pending_updates=True)

  # Запуск планировщика
  scheduler_service = SchedulerService(bot)
  scheduler_service.start()
  
  await dp.start_polling(bot)
