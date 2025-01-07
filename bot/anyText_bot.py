from aiogram import Bot
from aiogram import Router
from aiogram.types import Message
from utils.admin import get_admin_id
from utils.link_checker import check_if_text_is_feedback_link
from db.feedback import get_feedback, update_or_create_feedback
from utils.user_utils import get_user_name
from db.users import get_user
import settings.consts

router = Router()

@router.message()
async def handle_text_message(message: Message, bot: Bot):
  admin_id = get_admin_id()
  if (message.from_user.id != admin_id):
    #user_name = get_user_name(get_user(message.from_user.id))
    #await bot.send_message(admin_id, f"От пользователя {user_name}:")
    await message.forward(admin_id)

  if settings.consts.FEEDBACK_MODE:
    link = check_if_text_is_feedback_link(message)
    if link is not None:
      feedback = get_feedback(message.from_user.id)
      if feedback is None or feedback.link is None:
        is_update, feedback = update_or_create_feedback(message.from_user.id, link)
        await message.answer("Ваша ссылка проходит модерацию. Ожидайте ⏳")
        await bot.send_message(admin_id, f"Новая ссылка на отзыв от @{message.from_user.username}: {link}")
    