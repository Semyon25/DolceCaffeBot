from aiogram import Bot
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.enums import ParseMode
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from db.users import get_user
from utils.send_message import notify_admin
from utils.subcription_free_beverage import can_buy_subscription_today, get_active_subscription, is_used_code_today, get_unused_code_for_subscription
from utils.user_utils import get_user_name
from keyboards.main_menu import get_main_menu

router = Router()

class SubscriptionState(StatesGroup):
  waiting_payment = State()
  confirm_payment = State()

@router.message(F.text.lower() == "абонемент")
async def answer_purchase(message: Message, state: FSMContext):
  user_id = message.from_user.id
  subscription = get_active_subscription(user_id)
  # Если есть активный абонемент
  if subscription:
    # Если код уже использован сегодня
    if is_used_code_today(user_id):
      await message.answer("☕ Код уже использован сегодня — приходи за новым напитком завтра! 😊")
    # Если код не использован сегодня
    else:
      code = get_unused_code_for_subscription(user_id)
      await message.answer(f"☕ Сообщи бариста этот код для получения <b>бесплатного</b> напитка: <b>{code}</b> 😋", parse_mode=ParseMode.HTML)
  # Если нет активного абонемента
  elif can_buy_subscription_today():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Оплатить", callback_data="pay_for_subscription")
    ]])
    await message.answer("""<b>Абонемент DOLCE ☕</b> 🎁

Получи возможность брать <b>любой напиток бесплатно</b>
<b>каждый день до конца 2025 года!</b> 🌟

📅 Это значит, что <b>каждый день твой напиток обходится всего в 88 рублей!</b>

Для покупки абонемента нажми кнопку <b>ОПЛАТИТЬ</b> внизу данного сообщения.

После покупки нажми кнопку <b>АБОНЕМЕНТ</b> в чат-боте 💬
Бот пришлёт тебе <b>уникальный код</b> 🔢

Покажи этот <b>код бариста</b> — и получай свой <b>бесплатный</b> напиток каждый день ☕️

🎯 Абонемент действует до <b>31 декабря 2025 года</b>
<b>Один напиток в день — каждый день!</b> 💫

💳 Стоимость абонемента — всего <b>5000 рублей</b>

🔥 Акция действует <b>только сегодня!</b>
Не упусти шанс стать частью DOLCE! ❤️""", reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(SubscriptionState.waiting_payment)
  else:
    await message.answer("Покупка абонемента в настоящее время недоступна 😔", reply_markup=get_main_menu(message.from_user.id))

@router.callback_query(SubscriptionState.waiting_payment)
async def handle_waiting_payment(query: CallbackQuery, state: FSMContext, bot: Bot):
  if query.data == "pay_for_subscription":
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Проверить оплату", callback_data="confirm_payment_for_subscription")
    ]])
    await query.message.answer("<b>💳 Оплати абонемент</b>\n<a href=\"https://qr.nspk.ru/AD10000VSJ7BMQUT8N98DPTONNQUS8H4?type=02&bank=100000000004&sum=500000&cur=RUB&crc=C34E\">🔗 Перейти к оплате</a>\n<b>💰 Стоимость абонемента</b> — <b>5000 ₽</b>\n📸 <b>После оплаты</b> отправьте чек в этот бот и нажмите кнопку <i>«Проверить оплату»</i> ✅", reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(SubscriptionState.confirm_payment)    
    await bot.delete_message(chat_id=query.message.chat.id, message_id=query.message.message_id)
    await query.answer()

@router.callback_query(SubscriptionState.confirm_payment)
async def handle_confirm_payment(query: CallbackQuery, state: FSMContext, bot: Bot):
  if query.data == "confirm_payment_for_subscription":
    user = get_user(query.from_user.id)
    await notify_admin(bot, f"Пользователь {get_user_name(user)} ({int(user.id)}) купил абонемент! Необходимо проверить оплату и открыть абонемент")
    await query.message.answer("☕ Мы проверим оплату в течение нескольких часов. Спасибо за ваше терпение! 💛\n📩 Если появятся вопросы — напишите нам в этом боте, мы всегда на связи! 🤝")
    await bot.delete_message(chat_id=query.message.chat.id, message_id=query.message.message_id)
    await query.answer()
    await state.clear()