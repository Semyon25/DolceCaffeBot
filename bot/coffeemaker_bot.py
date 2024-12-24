from aiogram import Bot
from aiogram.fsm.state import StatesGroup, State
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from utils.admin import get_admin_id
from utils.user_utils import get_user_name, get_coffeemaker_emoji, get_feedback_emoji
from db.users import get_user, get_user_by_username, set_user_as_coffeemaker, get_users
from keyboards.main_menu import get_main_menu
from aiogram.filters import Command
from utils.code_generator import generate_code
from db.feedback import get_feedback, update_feedback_code, check_if_code_unique, confirm_code_usage, update_or_create_feedback

router = Router()

class CoffeemakerState(StatesGroup):
  entering_code = State()

@router.message(F.text.lower() == "ввести код")
async def enter_code(message: Message, state: FSMContext):
  user = get_user(message.from_user.id)
  if user is not None and user.is_coffeemaker == 1:
    await message.answer("Введите код клиента ⬇")
    await state.set_state(CoffeemakerState.entering_code)
  elif user is not None and user.is_coffeemaker == 0:
    await message.answer("Вы не можете ввести код",reply_markup=get_main_menu(user.id))

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
    userId = message.text.split()[1]
    user = get_user(userId)
    feedback = get_feedback(user.id)
    if feedback:
      code = generate_code()
      while not check_if_code_unique(code):
        code = generate_code()
      update_feedback_code(user.id, code)
      await bot.send_message(admin_id, f"Код для пользователя @{user.username}: {code}")
      await bot.send_message(user.id, f"Поздравляем! Ваш отзыв прошел модерацию! 🎉\nВаш код: {code}.\nСообщите этот код бариста и получите бесплатный напиток!", reply_markup=get_main_menu(user.id))
    else:
      await bot.send_message(admin_id, "Пользователь не найден.")

@router.message(Command('addNewCoffeemaker'))
async def add_new_coffeemaker(message: Message, bot: Bot):
  admin_id = int(get_admin_id())
  if message.from_user.id == admin_id:
    userId = message.text.split()[1]
    user = get_user(userId)
    if user is not None:
      if user.is_coffeemaker == 0:
        set_user_as_coffeemaker(user.id, 1)
        await bot.send_message(admin_id, "Добавлен новый бариста!")
        await bot.send_message(user.id, "Вам назначена роль бариста!",
                               reply_markup=get_main_menu(user.id))
      else:
        await bot.send_message(admin_id, "Данный пользователь уже бариста!")
    else:
      await bot.send_message(admin_id, "Такого пользователя не существует!")

@router.message(Command('removeCoffeemaker'))
async def remove_coffeemaker(message: Message, bot: Bot):
  admin_id = int(get_admin_id())
  if message.from_user.id == admin_id:
    userId = message.text.split()[1]
    user = get_user(userId)
    if user is not None:
      if user.is_coffeemaker == 1:
        set_user_as_coffeemaker(user.id, 0)
        await bot.send_message(admin_id, f"Пользователь @{user.username} больше не бариста!")
      else:
        await bot.send_message(admin_id, "Данный пользователь не бариста!")
    else:
      await bot.send_message(admin_id, "Такого пользователя не существует!")

@router.message(Command('allUsers'))
async def get_all_users(message: Message, bot: Bot):
  admin_id = int(get_admin_id())
  if message.from_user.id == admin_id:
    users = get_users()
    answer = ""
    number = 1
    # Сначала выводим бариста, а затем всех остальных
    sorted_users = sorted(users, key=lambda user: (-user.is_coffeemaker, user.id))
    for user in sorted_users:
      feedback = get_feedback(user.id)
      answer += f"{number}. {get_coffeemaker_emoji(user)} {get_user_name(user)} {get_feedback_emoji(feedback)}\n"
      number += 1
    await bot.send_message(admin_id, f"Список всех пользователей:\n{answer}")

@router.message(Command('addLink'))
async def add_link(message: Message, bot: Bot):
  admin_id = int(get_admin_id())
  if message.from_user.id == admin_id:
    userId = message.text.split()[1]
    user = get_user(userId)
    if user is not None:
      link = message.text.split()[2]
      is_update, feedback = update_or_create_feedback(user.id, link)
      if feedback is not None:
        await bot.send_message(admin_id, "Ссылка пользователю добавлена!")