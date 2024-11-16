from aiogram import Bot
from aiogram.fsm.state import StatesGroup, State
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from utils.admin import get_admin_id
from db.users import get_user, get_user_by_username, set_user_as_coffeemaker, get_users
from keyboards.main_menu import get_main_menu
from aiogram.filters import Command
from utils.code_generator import generate_code
from db.feedback import get_feedback, update_feedback_code, check_if_code_unique, confirm_code_usage

router = Router()

class CoffeemakerState(StatesGroup):
  entering_code = State()

@router.message(F.text.lower() == "ввести код")
async def enter_code(message: Message, state: FSMContext):
  await message.answer("Введите код клиента ⬇")
  await state.set_state(CoffeemakerState.entering_code)

@router.message(CoffeemakerState.entering_code)
async def check_code(message: Message, state: FSMContext, bot: Bot):
  confirm, user_id = confirm_code_usage(message.text)
  if confirm:
    await message.answer("✅ Код верный! ✅\nПриготовьте клиенту бесплатный напиток")
    user = get_user(user_id)
    await bot.send_message(get_admin_id(), f"Пользователь @{user.username} предъявил код для бесплатного напитка")
    await bot.send_message(user_id, "Код использован! Бариста приготовит вам бесплатный напиток!🥳☕", reply_markup=get_main_menu(user_id))
  else:
    await message.answer("❌ Код неверный! ❌", reply_markup=get_main_menu(message.from_user.id))
  await state.clear()


# Обработка команды /approve
@router.message(Command('approve'))
async def approve_feedback(message: Message, bot: Bot):
  admin_id = int(get_admin_id())
  if message.from_user.id == admin_id:
    username = message.text.split()[1]
    if username.startswith("@"):
      username = username[1:]
    user = get_user_by_username(username)
    feedback = get_feedback(user.id)
    if feedback:
      code = generate_code()
      while not check_if_code_unique(code):
        code = generate_code()
      update_feedback_code(user.id, code)
      await bot.send_message(admin_id, f"Код для пользователя @{user.username}: {code}")
      await bot.send_message(user.id, "Поздравляем! Ваш отзыв прошел модерацию! 🎉\nНажмите кнопку 'Получить код' и сообщите код бариста 🔢", reply_markup=get_main_menu(user.id))
    else:
      await bot.send_message(admin_id, "Пользователь не найден.")

@router.message(Command('addNewCoffeemaker'))
async def add_new_coffeemaker(message: Message, bot: Bot):
  admin_id = int(get_admin_id())
  if message.from_user.id == admin_id:
    username = message.text.split()[1]    
    if username.startswith("@"):
      username = username[1:]
    user = get_user_by_username(username)
    if user is not None:
      if user.is_coffeemaker == 0:
        set_user_as_coffeemaker(user.id)
        await bot.send_message(admin_id, "Добавлен новый бариста!")
      else:
        await bot.send_message(admin_id, "Данный пользователь уже бариста!")
    else:
      await bot.send_message(admin_id, "Такого пользователя не существует!")

@router.message(Command('allUsers'))
async def get_all_users(message: Message, bot: Bot):
  admin_id = int(get_admin_id())
  if message.from_user.id == admin_id:
    users = get_users()
    answer = ""
    for user in users:
      answer += f"@{user.username}|{user.tg_name}|{user.tg_surname}|{user.created_date}|{user.is_coffeemaker}\n"
    await bot.send_message(admin_id, f"Список всех пользователей:\n{answer}")