from aiogram import Bot
from aiogram.fsm.state import StatesGroup, State
from aiogram import types, Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from keyboards.main_menu import get_main_menu
from db.users import get_user, create_user
from db.feedback import get_feedback
from utils.admin import get_admin_id
from aiogram.enums import ParseMode
from utils.link_checker import check_if_text_is_feedback_link
from db.feedback import get_feedback, update_or_create_feedback

router = Router()

@router.message(F.text)
async def handle_text_message(message: Message, bot: Bot):
  admin_id = get_admin_id()
  if (message.from_user.id != admin_id):
    await bot.send_message(admin_id, f"От пользователя @{message.from_user.username}:\n{message.text}")
    
  link = check_if_text_is_feedback_link(message)
  if link is not None:
    feedback = get_feedback(message.from_user.id)
    if feedback is None or feedback.link is None:
      is_update, feedback = update_or_create_feedback(message.from_user.id, link)
      await message.answer("Ваша ссылка проходит модерацию. Ожидайте ⏳")
      await bot.send_message(admin_id, f"Новая ссылка на отзыв от @{message.from_user.username}: {link}")
    