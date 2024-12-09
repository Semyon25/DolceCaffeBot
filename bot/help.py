from aiogram import Bot
from aiogram.fsm.state import StatesGroup, State
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.types import FSInputFile
from aiogram.fsm.context import FSMContext
from keyboards.main_menu import get_main_menu
from db.users import get_user, create_user
from db.feedback import get_feedback
from utils.admin import get_admin_id

router = Router()

@router.message(Command("help"))
async def help(message: Message, bot: Bot):    
  admin_id = int(get_admin_id())
  if message.from_user.id == admin_id:
    await bot.send_message(admin_id, "/approve {username} - подтвердить ссылку на отзыв для пользователя\n/addNewCoffeemaker {username} - добавить бариста\n/removeCoffeemaker {username} - удалить бариста\n/allUsers - список всех пользователей")