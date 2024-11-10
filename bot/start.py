import os
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

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):    
    if (get_user(message.from_user.id) is None):
        create_user(message.from_user.id, message.from_user.username,
                    message.from_user.first_name, message.from_user.last_name)
    await message.answer(f"Привет, {message.from_user.first_name}! 👋\nЭто кофейня Dolce Caffe!☕🍫🥤 Здесь вы можете узнать последние новости кофейни и получить бесплатные напитки!🆓",
                         reply_markup=get_main_menu(message.from_user.id))


@router.message(F.text.lower() == "меню")
async def answer_menu(message: Message):
    photo1 = FSInputFile('Resources/TV - 48.jpg')
    photo2 = FSInputFile('Resources/TV - 49.jpg')
    await message.answer_photo(photo1)
    await message.answer_photo(photo2)





