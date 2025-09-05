import asyncio
from aiogram import Bot
from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from db.users import get_users, get_user
from utils.date_utils import get_next_week_range
from keyboards.shifts_keyboard import get_shifts_keyboard
from utils.user_utils import get_user_name
from utils.shifts import order_and_format_shifts
from utils.send_message import notify_admin_and_managers

router = Router()

# Задержка между отправками сообщений в секундах (чтобы не превысить лимиты Telegram)
DELAY_BETWEEN_MESSAGES = 1


async def plan_next_week(bot: Bot):
  users = get_users()
  start, end = get_next_week_range()
  for user in users:
    if user.is_coffeemaker == 1:
      await bot.send_message(user.id, f"👋 Добрый день!\n\n📅 Давайте запланируем ваш график на следующую неделю.\n✍️ Выберите, пожалуйста, смены, в которые вы сможете выйти на следующей неделе с <b>{start}</b> по <b>{end}</b>", parse_mode=ParseMode.HTML, reply_markup=get_shifts_keyboard())
      await asyncio.sleep(DELAY_BETWEEN_MESSAGES)

@router.callback_query(F.data.startswith("shift_"))
async def handle_shift_callback(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = callback.data

    user_data = await state.get_data()
    shifts = user_data.get("shifts", [])

    if data == "shift_none":
      if shifts:
        shifts = []
        await state.update_data(shifts=shifts)
        await callback.message.edit_reply_markup(reply_markup=get_shifts_keyboard(shifts))
      await callback.message.answer("На следующей неделе у вас нет смен 😢")
      await callback.answer()
      coffeemaker = get_user(callback.from_user.id)
      start, end = get_next_week_range("")
      await notify_admin_and_managers(bot, f"#planner #week_{start}_{end}\nБариста {get_user_name(coffeemaker)} отказался от смен на следующей неделе")
      return

    if data == "shift_submit":
        if not shifts:
            await callback.answer("Вы не выбрали смены ❌", show_alert=True)
            return
        await callback.message.answer("✅ Выбранные смены отправлены руководству!")
        await callback.answer()
        coffeemaker = get_user(callback.from_user.id)
        start, end = get_next_week_range("")
        await notify_admin_and_managers(bot, f"#planner #week_{start}_{end}\nБариста {get_user_name(coffeemaker)} выбрал смены:\n" + "\n".join(f"- {s}" for s in order_and_format_shifts(shifts)))
        await state.update_data(shifts=[])
        return

    # если это конкретная смена
    if data in shifts:
        shifts.remove(data)
    else:
        shifts.append(data)

    await state.update_data(shifts=shifts)

    # обновляем клавиатуру с галочками
    await callback.message.edit_reply_markup(reply_markup=get_shifts_keyboard(shifts))