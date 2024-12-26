import asyncio
from typing import List, Optional
from aiogram import Bot
from aiogram.fsm.state import StatesGroup, State
from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest, TelegramRetryAfter
from utils.admin import get_admin_id
from db.users import get_users

# Укажите задержку между отправками сообщений в секундах (чтобы не превысить лимиты Telegram)
DELAY_BETWEEN_MESSAGES = 1

router = Router()

class BroadcastState(StatesGroup):
  waiting_broadcast_content = State()
  waiting_confirmation = State()


@router.message(Command('broadcast'))
async def handle_broadcast_command(message: Message, state: FSMContext):
  admin_id = int(get_admin_id())
  if message.from_user.id == admin_id:
    await message.answer('Отправьте текст и/или фотографии для рассылки:')
    await state.set_state(BroadcastState.waiting_broadcast_content)


@router.message(BroadcastState.waiting_broadcast_content)
async def process_broadcast_text(message: Message, state: FSMContext):
  admin_id = int(get_admin_id())
  if message.from_user.id == admin_id:
    data = await state.get_data()
    text = data.get('broadcast_text')
    photos = data.get('broadcast_photos', [])
    if message.text:
      text = message.text
    if message.photo:
      photos.extend([photo.file_id for photo in message.photo])
    if not text and not photos:
      await message.answer("Пожалуйста, отправьте текст или фотографии.")
      return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Отправить",
                             callback_data="confirm_broadcast"),
        InlineKeyboardButton(text="Отменить", callback_data="cancel_broadcast")
    ]])
    if photos:
      media = []
      for i, photo in enumerate(photos):
        if i == 0 and text:
          media.append(InputMediaPhoto(media=photo, caption=text))
        else:
          media.append(InputMediaPhoto(media=photo))
      await message.answer_media_group(media=media, reply_markup=keyboard)
    elif text:
      await message.answer(text, reply_markup=keyboard)
    await state.update_data(broadcast_text=text, broadcast_photos=photos)
    await state.set_state(BroadcastState.waiting_confirmation)


@router.callback_query(BroadcastState.waiting_confirmation)
async def process_confirmation(query: CallbackQuery, state: FSMContext, bot: Bot):
  if query.data == "confirm_broadcast":
    data = await state.get_data()
    text = data.get('broadcast_text')
    photos = data.get('broadcast_photos')
    await query.message.answer("Начинаю рассылку...")
    errors = await send_message_to_all_users(bot, text, photos)
    if errors:
      error_message = "Возникли следующие ошибки при рассылке:\n\n" + "\n".join(errors)
      await query.message.answer(error_message)
    await query.message.answer('Рассылка завершена!')
    await query.answer()
  elif query.data == "cancel_broadcast":
    await query.message.answer("Рассылка отменена.")
    await query.answer()
  await state.clear()


async def send_message_to_all_users(bot: Bot, message_text: Optional[str], photos: Optional[List[str]] = None):
    users = get_users()
    all_errors = []
    for user in users:
      # for test
      if user.username != 'semyon_panichev' and user.username != 'TeacherEnglishDeutsch':
        continue
      
      errors = await send_message_to_user(bot, user.id, message_text, photos)
      if errors:
        all_errors.extend(errors)
      await asyncio.sleep(DELAY_BETWEEN_MESSAGES)
    return all_errors

async def send_message_to_user(bot: Bot, user_id: int, message_text: Optional[str], photos: Optional[List[str]] = None, errors: List[str] = []):
  try:
      if photos:
          media = []
          for i, photo in enumerate(photos):
              if i == 0 and message_text:
                  media.append(InputMediaPhoto(media=photo, caption=message_text))
              else:
                  media.append(InputMediaPhoto(media=photo))
          await bot.send_media_group(user_id, media=media)
      elif message_text:
          await bot.send_message(user_id, message_text)
  except TelegramForbiddenError:
    errors.append(f"Бот заблокирован пользователем {user_id}")
  except TelegramBadRequest as e:
    errors.append(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")
  except TelegramRetryAfter as e:
      await asyncio.sleep(e.retry_after)
      # Повторяем отправку после ожидания
      await send_message_to_user(bot, user_id, message_text, photos, errors)
  except Exception as e:
    errors.append(f"Неизвестная ошибка при отправке сообщения пользователю {user_id}: {e}")
  return errors