from aiogram import Bot
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from db.users import get_user
from utils.admin import is_admin, get_admin_ids, add_admin, remove_admin
from utils.send_message import notify_admin
from utils.user_utils import get_user_name
from keyboards.main_menu import get_main_menu

router = Router()


def get_user_id_from_command(message: Message) -> int | None:
  parts = (message.text or "").split()
  if len(parts) < 2 or not parts[1].isdigit():
    return None
  return int(parts[1])


async def send_message_safe(bot: Bot, user_id: int, text: str):
  # Пользователь мог заблокировать бота — это не должно ломать команду
  try:
    await bot.send_message(user_id, text, reply_markup=get_main_menu(user_id))
  except (TelegramForbiddenError, TelegramBadRequest):
    pass


@router.message(Command('admins'))
async def get_all_admins(message: Message):
  if is_admin(message.from_user.id):
    answer = "#admins\nАдминистраторы:\n"
    for number, admin_id in enumerate(get_admin_ids(), start=1):
      name = get_user_name(get_user(admin_id)) or "не зарегистрирован в боте"
      answer += f"{number}. {name} ({admin_id})\n"
    await message.answer(answer)


@router.message(Command('addAdmin'))
async def add_admin_handler(message: Message, bot: Bot):
  if is_admin(message.from_user.id):
    user_id = get_user_id_from_command(message)
    if user_id is None:
      await message.answer("⚠️ Укажи ID пользователя после команды: /addAdmin {userId}")
      return
    user = get_user(user_id)
    if user is None:
      await message.answer("❌ Такого пользователя не существует! Пользователь должен сначала запустить бота")
      return
    if not add_admin(user_id):
      await message.answer("🟡 Данный пользователь уже администратор!")
      return
    await notify_admin(bot, f"#admins\n✅ {get_user_name(get_user(message.from_user.id))} назначил администратором {get_user_name(user)} ({user_id})")
    await send_message_safe(bot, user_id, "Вам назначена роль администратора! Список команд: /help")


@router.message(Command('removeAdmin'))
async def remove_admin_handler(message: Message, bot: Bot):
  if is_admin(message.from_user.id):
    user_id = get_user_id_from_command(message)
    if user_id is None:
      await message.answer("⚠️ Укажи ID пользователя после команды: /removeAdmin {userId}")
      return
    # Запрещаем удалять себя, чтобы в боте всегда оставался хотя бы один администратор
    if user_id == message.from_user.id:
      await message.answer("⚠️ Нельзя снять роль администратора с самого себя!")
      return
    if not remove_admin(user_id):
      await message.answer("❌ Данный пользователь не администратор!")
      return
    user = get_user(user_id)
    await notify_admin(bot, f"#admins\n🗑 {get_user_name(get_user(message.from_user.id))} снял роль администратора с {get_user_name(user) or user_id} ({user_id})")
    await send_message_safe(bot, user_id, "С вас снята роль администратора")
