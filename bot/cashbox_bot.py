from aiogram import Bot
from aiogram.fsm.state import StatesGroup, State
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from db.users import get_user
from utils.admin import is_coffeemaker_or_admin
from utils.send_message import notify_admin
from utils.number_utils import to_float
from utils.user_utils import get_user_name
from aiogram.enums import ParseMode
from keyboards.main_menu import get_main_menu
from datetime import date

router = Router()


class CashboxState(StatesGroup):
  entering_operation_type = State()
  entering_cash_balance = State()
  entering_cash_flow = State()


@router.message(F.text.lower() == "касса")
async def cash_operations_handle(message: Message, state: FSMContext):
  if is_coffeemaker_or_admin(message.from_user.id):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💰 Остаток", callback_data="cash_balance"),
        InlineKeyboardButton(text="💸 Расход", callback_data="cash_flow")
    ]])
    await message.answer("""Выберите тип операции:
    💰 Ввести остаток денег в кассе
    💸 Ввести расход денег в кассе (на покупку или ЗП)""",
                         reply_markup=keyboard)
    await state.set_state(CashboxState.entering_operation_type)
  else:
    await message.answer("Доступ ограничен",
                         reply_markup=get_main_menu(message.from_user.id))


@router.callback_query(CashboxState.entering_operation_type)
async def entering_operation_type_handle(query: CallbackQuery,
                                         state: FSMContext, bot: Bot):
  if query.data == "cash_balance":
    await query.message.answer("Введите остаток денег в кассе ⬇")
    await state.set_state(CashboxState.entering_cash_balance)
  elif query.data == "cash_flow":
    await query.message.answer("Введите расход по кассе ⬇")
    await state.set_state(CashboxState.entering_cash_flow)
  else:
    await state.clear()
  await bot.delete_message(chat_id=query.message.chat.id,
                           message_id=query.message.message_id)
  await query.answer()

@router.message(CashboxState.entering_cash_balance)
async def entering_cash_balance_handle(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    entered_amount = to_float(message.text or '')
    if entered_amount is not None and entered_amount > 0:
      coffeemaker = get_user(message.from_user.id)
      today = date.today().strftime("%d.%m.%Y")
      await notify_admin(bot,
          f"#cash_balance\n💰{today}: Бариста {get_user_name(coffeemaker)} указал остаток по кассе: <b>{entered_amount}</b> ₽", parse_mode=ParseMode.HTML)
      await message.answer("✅ Остаток записан! ✅")
    else:
      await message.answer("❌ Некорректный ввод! ❌\nПожалуйста, введите корректное значение!")

@router.message(CashboxState.entering_cash_flow)
async def entering_cash_flow_handle(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    entered_amount = to_float(message.text or '')
    if entered_amount is not None and entered_amount > 0:
      coffeemaker = get_user(message.from_user.id)
      today = date.today().strftime("%d.%m.%Y")
      await notify_admin(bot,
          f"#cash_flow\n📤{today}: Бариста {get_user_name(coffeemaker)} указал расход по кассе: <b>{entered_amount}</b> ₽", parse_mode=ParseMode.HTML)
      await message.answer("✅ Расход записан! ✅\nЕсли у вас есть чек, отправьте его в боте!")
    else:
      await message.answer("❌ Некорректный ввод! ❌\nПожалуйста, введите корректное значение!")