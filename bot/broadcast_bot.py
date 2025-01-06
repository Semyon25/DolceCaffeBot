import asyncio
from typing import List, Optional
from aiogram import Bot
from aiogram.fsm.state import StatesGroup, State
from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest, TelegramRetryAfter
from utils.admin import get_admin_id
from db.users import User, get_user, get_users
from utils.user_utils import get_user_name

# Укажите задержку между отправками сообщений в секундах (чтобы не превысить лимиты Telegram)
DELAY_BETWEEN_MESSAGES = 1

router = Router()

class BroadcastState(StatesGroup):
  waiting_broadcast_content = State()
  waiting_confirmation = State()

@router.message(Command('sendMessage'))
async def handle_sendMessage_command(message: Message, state: FSMContext):
  admin_id = int(get_admin_id())
  if message.from_user.id == admin_id:
    userId = message.text.split()[1]
    user = get_user(userId)
    if user is not None:
      await state.update_data(user_id=user.id)
      await message.answer('Отправьте текст и/или фотографии для рассылки:')
      await state.set_state(BroadcastState.waiting_broadcast_content)


@router.message(Command('broadcast'))
async def handle_broadcast_command(message: Message, state: FSMContext):
  admin_id = int(get_admin_id())
  if message.from_user.id == admin_id:
    await message.answer('Отправьте текст и/или фотографии для рассылки:')
    await state.set_state(BroadcastState.waiting_broadcast_content)


@router.message(BroadcastState.waiting_broadcast_content)
async def process_broadcast_content(message: Message, state: FSMContext):
  admin_id = int(get_admin_id())
  if message.from_user.id == admin_id:
    text = message.text
    photos = []
    if message.photo is not None:
      photos = [photo.file_id for photo in message.photo]
      text = message.caption
    if not text and not photos:
      await message.answer("Пожалуйста, отправьте текст или фотографии.")
      return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Отправить",
                             callback_data="confirm_broadcast"),
        InlineKeyboardButton(text="Отменить", callback_data="cancel_broadcast")
    ]])
    if photos:
      media_builder = MediaGroupBuilder(caption=text)
      media_builder.add_photo(media=photos[-1])
      await message.answer_media_group(media=media_builder.build())
      await message.answer('Отправить?', reply_markup=keyboard)
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
    user_id = data.get('user_id')
    await query.message.answer("Начинаю отправку...")
    errors = await send_message_to_users(bot, user_id, text, photos)
    if errors:
      error_message = "Возникли следующие ошибки при рассылке:\n\n" + "\n".join(errors)
      await query.message.answer(error_message)
    await query.message.answer('Отправка завершена!')
    await query.answer()
  elif query.data == "cancel_broadcast":
    await query.message.answer("Отправка отменена.")
    await query.answer()
  await query.message.edit_reply_markup(reply_markup=None) # Убираем кнопки
  await state.clear()


async def send_message_to_users(bot: Bot, userId: int, message_text: Optional[str], photos: Optional[List[str]] = None):
    users = [get_user(userId)] if userId is not None else get_users()
    all_errors = []
    for user in users:        
      errors = await send_message_to_user(bot, user, message_text, photos, [])
      if errors:
        all_errors.extend(errors)
      await asyncio.sleep(DELAY_BETWEEN_MESSAGES)
    return all_errors

async def send_message_to_user(bot: Bot, user: User, message_text: Optional[str], photos: Optional[List[str]], errors: List[str]):
  try:
    if photos:
      media_builder = MediaGroupBuilder(caption=message_text)
      media_builder.add_photo(media=photos[-1])
      await bot.send_media_group(user.id, media=media_builder.build())
    elif message_text:
      await bot.send_message(user.id, message_text)
  except TelegramForbiddenError:
    errors.append(f"Бот заблокирован пользователем {get_user_name(user)}")
  except TelegramBadRequest as e:
    errors.append(f"Ошибка при отправке сообщения пользователю {get_user_name(user)}: {e}")
  except TelegramRetryAfter as e:
    await asyncio.sleep(e.retry_after)
    # Повторяем отправку после ожидания
    await send_message_to_user(bot, user, message_text, photos, errors)
  except Exception as e:
    errors.append(f"Неизвестная ошибка при отправке сообщения пользователю {get_user_name(user)}: {e}")
  return errors