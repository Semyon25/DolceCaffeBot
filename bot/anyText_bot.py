from aiogram import Bot
from aiogram import Router
from aiogram.types import Message
from utils.admin import is_admin, get_admin_ids
from utils.send_message import notify_admin
from utils.link_checker import check_if_text_is_feedback_link
from db.feedback import get_feedback, update_or_create_feedback
import settings.consts
from services.schedule_parser import parse_schedule
from services.schedule_storage import load_schedule, save_schedule

router = Router()

@router.message()
async def handle_text_message(message: Message, bot: Bot):
  if is_admin(message.from_user.id):
    await schedule_message_handler(message,bot)
  else:
    for admin_id in get_admin_ids():
      await message.forward(admin_id)

  if settings.consts.FEEDBACK_MODE:
    link = check_if_text_is_feedback_link(message)
    if link is not None:
      feedback = get_feedback(message.from_user.id)
      if feedback is None or feedback.link is None:
        is_update, feedback = update_or_create_feedback(message.from_user.id, link)
        await message.answer("Ваша ссылка проходит модерацию. Ожидайте ⏳")
        await notify_admin(bot, f"Новая ссылка на отзыв от @{message.from_user.username}: {link}")


async def schedule_message_handler(message: Message, bot: Bot):
  if not message.text or "Расписание на неделю" not in message.text:
    return
  parsed = parse_schedule(message.text)
  if not parsed:
      return
  schedule = load_schedule()
  schedule.update(parsed)
  save_schedule(schedule)

  await message.answer("Расписание сохранено ✅")