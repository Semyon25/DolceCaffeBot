import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram import F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.enums import ParseMode
import start, feedback_bot, coffeemaker_bot

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
