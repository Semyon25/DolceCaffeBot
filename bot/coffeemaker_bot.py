import asyncio
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.fsm.state import StatesGroup, State
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from utils.admin import get_admin_id, is_coffeemaker_or_admin
from utils.user_utils import get_user_name, get_coffeemaker_emoji, get_feedback_emoji, get_beverage_count_emoji
from db.users import get_user, set_user_as_coffeemaker, get_users
from keyboards.main_menu import get_main_menu
from utils.code_generator import generate_code_6, generate_purchase_code_if_needed
from utils.declension_noun import beverage_declension
from db.feedback import get_feedback, update_feedback_code, check_if_code_unique as check_if_code_unique_from_feedback, confirm_code_usage as confirm_code_usage_from_feedback, update_or_create_feedback
from db.codes import get_user as get_user_by_code, confirm_code_usage, check_if_code_unique, set_code
from db.purchases import get_count, set_count

router = Router()


class CoffeemakerState(StatesGroup):
  entering_code = State()
  waiting_beverage_count = State()


@router.message(F.text.lower() == "ввести код")
async def enter_code(message: Message, state: FSMContext):
  if is_coffeemaker_or_admin(message.from_user.id):
    await message.answer("Введите код клиента ⬇")
    await state.set_state(CoffeemakerState.entering_code)
  else:
    await message.answer("Вы не можете ввести код",
                         reply_markup=get_main_menu(message.from_user.id))


@router.message(CoffeemakerState.entering_code)
async def check_code(message: Message, state: FSMContext, bot: Bot):
  await state.clear()
  entered_code = message.text or ''
  # Акция 6+1
  if entered_code.isdigit() and len(entered_code) == 4:
    await handle_purchase_6_1(message, state, bot)
  # Напиток за отзыв
  elif entered_code.isdigit() and (len(entered_code) == 6):
    await handle_feedback(message, bot)
  # Сертификат с кодом
  elif entered_code.isdigit() and (len(entered_code) == 8):
    await handle_certificate(message, bot)
  else:
    await message.answer("❌ Код неверный! ❌\nПожалуйста, проверьте введенный код и повторите попытку!")


# Обработчик ввода кода по акции 6+1
async def handle_purchase_6_1(message: Message, state: FSMContext, bot: Bot):
  entered_code = message.text or ''
  userId = get_user_by_code(entered_code)
  if userId is None:
    await message.answer(
        "❌ Код уже был использован! Необходимо клиенту сгенерировать новый код (нажать кнопку 'Акция 6+1')"
    )
  else:
    count = get_count(userId)
    confirm_code_usage(entered_code)
    if count is not None and count >= 6:
      set_count(userId, 0)
      await message.answer(
          "✅ Код верный! ✅\nПриготовьте клиенту бесплатный напиток")
      client = get_user(userId)
      await bot.send_message(
          get_admin_id(),
          f"Пользователь {get_user_name(client)} предъявил код для бесплатного напитка по акции 6+1"
      )
      await bot.send_message(userId,
                             "Бариста приготовит вам бесплатный напиток!🥳☕")
    elif count is not None and count < 6:
      await state.update_data(user_id=userId, count=count)
      keyboard = InlineKeyboardMarkup(inline_keyboard=[[
          InlineKeyboardButton(text="1", callback_data="beverage_1"),
          InlineKeyboardButton(text="2", callback_data="beverage_2"),
          InlineKeyboardButton(text="3", callback_data="beverage_3")
      ]])
      await message.answer(
          "✅ Код верный! ✅\nВыберите, сколько напитков купил клиент",
          reply_markup=keyboard)
      await state.set_state(CoffeemakerState.waiting_beverage_count)


@router.callback_query(CoffeemakerState.waiting_beverage_count)
async def handle_beverage_count(query: CallbackQuery, state: FSMContext,
                                bot: Bot):
  delta = int(0)
  if query.data == "beverage_1":
    delta = 1
  elif query.data == "beverage_2":
    delta = 2
  elif query.data == "beverage_3":
    delta = 3
  data = await state.get_data()
  userId = data.get('user_id')
  count = min(6, data.get('count') + delta)
  set_count(userId, count)
  user = get_user(userId)
  await bot.send_message(
      get_admin_id(),
      f"Пользователь {get_user_name(user)} купил {delta} {beverage_declension(delta)} по акции 6+1. Общее количество напитков: {count}"
  )
  await bot.send_message(
      userId,
      f"✅ Покупка учтена! Вы накопили <b>{count}</b> {beverage_declension(count)} из 6.☕",
      parse_mode=ParseMode.HTML)
  if count >= 6:
    code = generate_purchase_code_if_needed(userId)
    await bot.send_message(
        userId,
        f'🎉 <b>Поздравляем!</b> 🎉\nВы накопили шесть напитков! Вам доступен <b>бесплатный напиток</b>!☕\nЧтобы получить бесплатный напиток, сообщите бариста код <b>{code}</b>',
        parse_mode=ParseMode.HTML)
  await query.message.answer("✅ Покупка клиента учтена!")
  await bot.delete_message(chat_id=query.message.chat.id,
                           message_id=query.message.message_id)
  await query.answer()
  await state.clear()


# Обработчик ввода кода по напиток за отзыв
async def handle_feedback(message: Message, bot: Bot):
  entered_code = message.text or ''
  confirm, user_id = confirm_code_usage_from_feedback(entered_code)
  if confirm:
    await message.answer(
        "✅ Код верный! ✅\nПриготовьте клиенту бесплатный напиток")
    user = get_user(user_id)
    await bot.send_message(
        get_admin_id(),
        f"Пользователь @{user.username} предъявил код для бесплатного напитка")
    await bot.send_message(
        user_id,
        "Код использован! Бариста приготовит вам бесплатный напиток!🥳☕",
        reply_markup=get_main_menu(user_id))
  else:
    await message.answer("❌ Код неверный! ❌",
                         reply_markup=get_main_menu(message.from_user.id))


# Обработчик ввода кода по сертификату
async def handle_certificate(message: Message, bot: Bot):
  entered_code = message.text or ''
  user_id = get_user_by_code(entered_code)
  if user_id == get_admin_id():
    confirm_code_usage(entered_code)
    await message.answer("✅ Код верный! ✅\nПриготовьте клиенту бесплатный напиток")
    await bot.send_message(user_id, f"Использован код {entered_code} по сертификату на бесплатный напиток")
  else:
    await message.answer("❌ Код неверный! ❌",
                         reply_markup=get_main_menu(message.from_user.id))


# Обработка команды /approve
@router.message(Command('approve'))
async def approve_feedback(message: Message, bot: Bot):
  admin_id = int(get_admin_id())
  if message.from_user.id == admin_id:
    userId = message.text.split()[1]
    user = get_user(userId)
    feedback = get_feedback(user.id)
    if feedback:
      code = generate_code_6()
      while not check_if_code_unique_from_feedback(code):
        code = generate_code_6()
      update_feedback_code(user.id, code)
      await bot.send_message(admin_id,
                             f"Код для пользователя @{user.username}: {code}")
      await bot.send_message(
          user.id,
          f"Поздравляем! Ваш отзыв прошел модерацию! 🎉\nВаш код: {code}.\nСообщите этот код бариста и получите бесплатный напиток!",
          reply_markup=get_main_menu(user.id))
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
        await bot.send_message(user.id,
                               "Вам назначена роль бариста!",
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
        await bot.send_message(
            admin_id, f"Пользователь @{user.username} больше не бариста!")
      else:
        await bot.send_message(admin_id, "Данный пользователь не бариста!")
    else:
      await bot.send_message(admin_id, "Такого пользователя не существует!")


@router.message(Command('allUsers'))
async def get_all_users(message: Message, bot: Bot):
  admin_id = int(get_admin_id())
  if message.from_user.id == admin_id:
    users = get_users()
    answer = f"#allUsers\nВсего в боте {users.count} пользователей:\n"
    number = 1
    # Сначала выводим бариста, а затем всех остальных
    sorted_users = sorted(users, key=lambda user: -user.is_coffeemaker)
    for user in sorted_users:
      feedback = get_feedback(user.id)
      beverage_count = get_count(user.id)
      answer += f"{number}. {get_coffeemaker_emoji(user)} {get_user_name(user)} ({int(user.id)}){get_feedback_emoji(feedback)} {get_beverage_count_emoji(beverage_count)}\n"
      if number % 90 == 0:
        await bot.send_message(admin_id, answer)
        await asyncio.sleep(1)
        answer = ""
      number += 1
    if answer != "":
      await bot.send_message(admin_id, answer)


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


@router.message(Command('correctPurchaseCount'))
async def correct_purchase_count(message: Message, bot: Bot):
  admin_id = int(get_admin_id())
  if message.from_user.id == admin_id:
    userId = message.text.split()[1]
    user = get_user(userId)
    if user is not None:
      count = message.text.split()[2]
      set_count(userId, count)
      updated_count = get_count(userId)
      await bot.send_message(
          admin_id, f"У пользователя накоплено {updated_count} напитков")


@router.message(Command('addNewCode'))
async def add_new_code(message: Message, bot: Bot):
  admin_id = int(get_admin_id())
  if message.from_user.id == admin_id:
    code = message.text.split()[1]
    if len(code) != 8:
      await bot.send_message(admin_id, "Введите 8-значный код!")
      return
    if check_if_code_unique(code):
      set_code(admin_id, code)  # записываю код на себя
      await bot.send_message(admin_id, "Код добавлен в базу!")
    else:
      await bot.send_message(admin_id, "Введенный код не уникальный!")
