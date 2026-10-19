import asyncio
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.fsm.state import StatesGroup, State
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from bot.feedback_bot import use_code
from bot.planner import plan_next_week, get_default_wishes_week, get_shift_wishes_text, get_last_day_text
from utils.admin import is_admin, is_coffeemaker_or_admin
from utils.send_message import notify_admin
from utils.user_utils import get_user_name, get_coffeemaker_emoji, get_feedback_emoji, get_beverage_count_emoji
from db.users import get_user, set_user_as_coffeemaker, get_users, set_name_for_user
from keyboards.main_menu import get_main_menu
from keyboards.schedule_keyboard import get_shift_wishes_keyboard
from db.shift_schedule import is_schedule_published
from utils.date_utils import get_next_week_start
from utils.code_generator import generate_code_6, generate_purchase_code_if_needed
from utils.declension_noun import beverage_declension
from db.feedback import get_feedback, update_feedback_code, check_if_code_unique as check_if_code_unique_from_feedback, confirm_code_usage as confirm_code_usage_from_feedback, update_or_create_feedback
from db.codes import get_user as get_user_by_code, confirm_code_usage, check_if_code_unique, set_code
from db.purchases import get_count, set_count
from utils.subcription_free_beverage import use_code_for_subscription, create_subscription_until_end_2025, get_active_subscription

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
  # Абонемент
  elif entered_code.isdigit() and (len(entered_code) == 5):
    await handle_subscription(message, bot)
  else:
    await message.answer(
        "❌ Код неверный! ❌\nПожалуйста, проверьте введенный код и повторите попытку!"
    )


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
      coffeemaker = get_user(message.from_user.id)
      await notify_admin(
          bot,
          f"Пользователь {get_user_name(client)} предъявил бариста {get_user_name(coffeemaker)} код для бесплатного напитка по акции 6+1"
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
  coffeemaker = get_user(query.from_user.id)
  await notify_admin(
      bot,
      f"Пользователь {get_user_name(user)} купил {delta} {beverage_declension(delta)} по акции 6+1 у бариста {get_user_name(coffeemaker)}. Общее количество напитков: {count}"
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
    await notify_admin(
        bot,
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
  if user_id is not None and is_admin(user_id):
    confirm_code_usage(entered_code)
    await message.answer(
        "✅ Код верный! ✅\nПриготовьте клиенту бесплатный напиток")
    await notify_admin(
        bot,
        f"Использован код {entered_code} по сертификату на бесплатный напиток")
  else:
    await message.answer("❌ Код неверный! ❌",
                         reply_markup=get_main_menu(message.from_user.id))

# Обработчик ввода кода по абонементу
async def handle_subscription(message: Message, bot: Bot):
  entered_code = message.text or ''
  (user_id, error) = use_code_for_subscription(entered_code)
  if error:
    await message.answer(f"❌ Код неверный! {error} ❌")
    return
  if user_id:
    await message.answer("✅ Код верный! ✅\nПриготовьте клиенту бесплатный напиток")
    await bot.send_message(user_id, "Код использован! Бариста приготовит вам бесплатный напиток!🥳☕")
    await notify_admin(bot, f"Пользователь {get_user_name(get_user(user_id))} предъявил код для бесплатного напитка по абонементу")

def get_command_args(message: Message, maxsplit: int = -1) -> list[str]:
  """Возвращает параметры команды без самой команды"""
  return (message.text or "").split(maxsplit=maxsplit)[1:]


async def approve_feedback_for_user(message: Message, bot: Bot, user_id):
  """Подтверждает отзыв пользователя и отправляет ему код на бесплатный напиток"""
  user = get_user(user_id)
  feedback = get_feedback(user.id) if user is not None else None
  if feedback:
    code = generate_code_6()
    while not check_if_code_unique_from_feedback(code):
      code = generate_code_6()
    update_feedback_code(user.id, code)
    await message.answer(f"Код для пользователя @{user.username}: {code}")
    await bot.send_message(
        user.id,
        f"Поздравляем! Ваш отзыв прошел модерацию! 🎉\nВаш код: {code}.\nСообщите этот код бариста и получите бесплатный напиток!",
        reply_markup=get_main_menu(user.id))
  else:
    await message.answer("Пользователь не найден.")


async def add_coffeemaker(message: Message, bot: Bot, user_id, name: str | None = None):
  """Назначает пользователя бариста и, если указано, задаёт ему имя"""
  user = get_user(user_id)
  if user is None:
    await message.answer("Такого пользователя не существует!")
    return
  if user.is_coffeemaker == 0:
    set_user_as_coffeemaker(user.id, 1)
    await message.answer("Добавлен новый бариста!")
    await bot.send_message(user.id,
                           "Вам назначена роль бариста!",
                           reply_markup=get_main_menu(user.id))
  else:
    await message.answer("Данный пользователь уже бариста!")
  if name:
    set_name_for_user(user.id, name)
    await message.answer("Задано имя для бариста!")


async def remove_coffeemaker_by_id(message: Message, user_id):
  """Снимает с пользователя роль бариста"""
  user = get_user(user_id)
  if user is not None:
    if user.is_coffeemaker == 1:
      set_user_as_coffeemaker(user.id, 0)
      await message.answer(
          f"Пользователь @{user.username} больше не бариста!")
    else:
      await message.answer("Данный пользователь не бариста!")
  else:
    await message.answer("Такого пользователя не существует!")


async def send_coffeemakers_list(message: Message):
  """Отправляет список бариста"""
  users = get_users()
  answer = f"#allUsers\nВсего в боте {len(users)} пользователей.\nБариста:\n"
  number = 1
  # Отбираем только бариста
  coffeemakers = [user for user in users if user.is_coffeemaker]
  for user in coffeemakers:
    answer += f"{number}. {get_coffeemaker_emoji(user)} {get_user_name(user)} ({int(user.id)})\n"
    number += 1
  await message.answer(answer)


async def send_all_users_in_details(message: Message):
  """Отправляет список всех пользователей с отзывами и накопленными напитками"""
  users = get_users()
  answer = f"#allUsers\nВсего в боте {len(users)} пользователей:\n"
  number = 1
  # Сначала выводим бариста, а затем всех остальных
  sorted_users = sorted(users, key=lambda user: -user.is_coffeemaker)
  for user in sorted_users:
    feedback = get_feedback(user.id)
    beverage_count = get_count(user.id)
    answer += f"{number}. {get_coffeemaker_emoji(user)} {get_user_name(user)} ({int(user.id)}){get_feedback_emoji(feedback)} {get_beverage_count_emoji(beverage_count)}\n"
    if number % 90 == 0:
      await message.answer(answer)
      await asyncio.sleep(1)
      answer = ""
    number += 1
  if answer != "":
    await message.answer(answer)


async def add_feedback_link(message: Message, user_id, link: str):
  """Добавляет пользователю ссылку на отзыв"""
  user = get_user(user_id)
  if user is None:
    await message.answer("Такого пользователя не существует!")
    return
  is_update, feedback = update_or_create_feedback(user.id, link)
  if feedback is not None:
    await message.answer("Ссылка пользователю добавлена!")


async def correct_purchase_count_for_user(message: Message, user_id, count: str) -> bool:
  """
  Изменяет количество накопленных напитков по акции 6+1. Возвращает False, если ввод некорректный.
  """
  user = get_user(user_id)
  if user is None:
    await message.answer("Такого пользователя не существует!")
    return False
  if not count.isdigit() or int(count) > 6:
    await message.answer("⚠️ Количество напитков должно быть числом от 0 до 6!")
    return False
  set_count(user.id, int(count))
  updated_count = get_count(user.id)
  await message.answer(
      f"У пользователя накоплено {updated_count} напитков")
  return True


async def add_certificate_code(message: Message, admin_id: int, code: str) -> bool:
  """
  Добавляет в базу 8-значный код сертификата. Возвращает False, если код не добавлен.
  """
  if len(code) != 8 or not code.isdigit():
    await message.answer("Введите 8-значный код!")
    return False
  if check_if_code_unique(code):
    set_code(admin_id, code)  # записываю код на администратора
    await message.answer("Код добавлен в базу!")
    return True
  await message.answer("Введенный код не уникальный!")
  return False


async def send_plan_next_week(message: Message, bot: Bot):
  """Отправляет бариста сообщение о планировании следующей недели и присылает отчёт"""
  if is_schedule_published(get_next_week_start()):
    await message.answer("⛔ Расписание на следующую неделю уже опубликовано, выбор смен закрыт")
    return
  await message.answer("Начинаю отправку бариста сообщения о планировании...")
  sent, failed, skipped = await plan_next_week(bot)
  report = (f"📅 Приём пожеланий на следующую неделю открыт до конца воскресенья {get_last_day_text(get_next_week_start())}\n\n"
            f"✅ Сообщение о планировании следующей недели отправлено бариста: {len(sent)}")
  if sent:
    report += "\n" + "\n".join(f"- {name}" for name in sent)
  if skipped:
    report += f"\n\n👌 Уже выбрали смены: {len(skipped)}\n" + "\n".join(f"- {name}" for name in skipped)
  if failed:
    report += f"\n\n❌ Не удалось отправить: {len(failed)}\n" + "\n".join(f"- {error}" for error in failed)
  await message.answer(report)


async def send_shift_wishes(message: Message):
  """Присылает сводку пожеланий бариста по сменам с переключением недель"""
  week_start = get_default_wishes_week()
  await message.answer(get_shift_wishes_text(week_start), parse_mode=ParseMode.HTML,
                       reply_markup=get_shift_wishes_keyboard(week_start))


async def add_subscription_for_user(message: Message, bot: Bot, user_id):
  """Добавляет пользователю абонемент на ежедневный бесплатный напиток"""
  user = get_user(user_id)
  if user is None:
    await message.answer("❌ Пользователь не найден!")
    return
  sub = get_active_subscription(user.id)
  if sub is not None:
    await message.answer("🟡 У пользователя уже есть активный абонемент!")
    return
  if create_subscription_until_end_2025(user.id):
    await message.answer(f"✅ Абонемент успешно добавлен пользователю {get_user_name(user)}!")
    await bot.send_message(user.id, "🥳 Вам добавлен абонемент на ежедневный бесплатный напиток до конца 2025 года! ☕✨")
  else:
    await message.answer("⚠️ Не удалось добавить абонемент!")


# Обработка команды /approve
@router.message(Command('approve'))
async def approve_feedback(message: Message, bot: Bot):
  if is_admin(message.from_user.id):
    args = get_command_args(message)
    if not args:
      await message.answer("⚠️ Укажи ID пользователя после команды: /approve {userId}")
      return
    await approve_feedback_for_user(message, bot, args[0])


@router.message(Command('addNewCoffeemaker'))
async def add_new_coffeemaker(message: Message, bot: Bot):
  if is_admin(message.from_user.id):
    # Имя бариста может состоять из нескольких слов
    args = get_command_args(message, maxsplit=2)
    if not args:
      await message.answer("⚠️ Укажи ID пользователя после команды: /addNewCoffeemaker {userId} [{name}]")
      return
    name = args[1] if len(args) > 1 else None
    await add_coffeemaker(message, bot, args[0], name)


@router.message(Command('removeCoffeemaker'))
async def remove_coffeemaker(message: Message, bot: Bot):
  if is_admin(message.from_user.id):
    args = get_command_args(message)
    if not args:
      await message.answer("⚠️ Укажи ID пользователя после команды: /removeCoffeemaker {userId}")
      return
    await remove_coffeemaker_by_id(message, args[0])


@router.message(Command('allUsers'))
async def get_all_users(message: Message, bot: Bot):
  if is_admin(message.from_user.id):
    await send_coffeemakers_list(message)


@router.message(Command('allUsersInDetails'))
async def get_all_users_in_details(message: Message, bot: Bot):
  if is_admin(message.from_user.id):
    await send_all_users_in_details(message)


@router.message(Command('addLink'))
async def add_link(message: Message, bot: Bot):
  if is_admin(message.from_user.id):
    args = get_command_args(message)
    if len(args) < 2:
      await message.answer("⚠️ Укажи ID пользователя и ссылку после команды: /addLink {userId} {link}")
      return
    await add_feedback_link(message, args[0], args[1])


@router.message(Command('correctPurchaseCount'))
async def correct_purchase_count(message: Message, bot: Bot):
  if is_admin(message.from_user.id):
    args = get_command_args(message)
    if len(args) < 2:
      await message.answer("⚠️ Укажи ID пользователя и количество напитков после команды: /correctPurchaseCount {userId} {count}")
      return
    await correct_purchase_count_for_user(message, args[0], args[1])


@router.message(Command('addNewCode'))
async def add_new_code(message: Message, bot: Bot):
  if is_admin(message.from_user.id):
    args = get_command_args(message)
    if not args:
      await message.answer("⚠️ Укажи код после команды: /addNewCode {code}")
      return
    await add_certificate_code(message, message.from_user.id, args[0])


@router.message(Command('planNextWeek'))
async def planNextWeek_handler(message: Message, bot: Bot):
  if is_admin(message.from_user.id):
    await send_plan_next_week(message, bot)


@router.message(Command('shiftWishes'))
async def shiftWishes_handler(message: Message):
  if is_admin(message.from_user.id):
    await send_shift_wishes(message)


@router.message(Command('add_subscription'))
async def add_subscription_handler(message: Message, bot: Bot):
  if is_admin(message.from_user.id):
    args = get_command_args(message)
    if not args:
      await message.answer("⚠️ Укажи ID пользователя после команды")
      return
    await add_subscription_for_user(message, bot, args[0])
