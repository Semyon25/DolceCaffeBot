from aiogram import Bot
from aiogram.fsm.state import StatesGroup, State
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from db.feedback import get_feedback, update_or_create_feedback, update_feedback_code, check_if_code_unique
from utils.admin import get_admin_id
from utils.code_generator import generate_code
from keyboards.main_menu import get_main_menu

router = Router()

class OrderFeedback(StatesGroup):
  waiting_for_link = State()

@router.message(F.text.lower() == "оставить отзыв")
async def answer_feedback(message: Message, state: FSMContext):
    await message.answer("Введите ссылку на ваш отзыв⤵️")
    await state.set_state(OrderFeedback.waiting_for_link)


@router.message(OrderFeedback.waiting_for_link)
async def link_sended(message: Message, state: FSMContext, bot: Bot):
    # Если entities вообще нет, вернётся None,
    # в этом случае считаем, что это пустой список
    entities = message.entities or []
    # Если есть хотя бы одна ссылка, возвращаем её
    link = None
    for entity in entities:
        if entity.type == "url":
            link = entity.extract_from(message.text)

    if link is not None:
        admin_id = get_admin_id()
        is_update, feedback = update_or_create_feedback(message.from_user.id,
                                                     link)
        if is_update:
          await message.answer("Ваша ссылка обновлена и находится на модерации. Ожидайте ⏳")
          await bot.send_message(
              admin_id,
              f"Обновленная ссылка на отзыв от @{message.from_user.username}: {link}"
          )
        else:
          await message.answer("Ваша ссылка проходит модерацию. Ожидайте ⏳")
          await bot.send_message(
              admin_id,
              f"Новая ссылка на отзыв от @{message.from_user.username}: {link}"
          )
        await state.clear()
    else:
        await message.answer(
            "❌ Некорректная ссылка ❌\nПожалуйста, введите ссылку на ваш отзыв еще раз")

@router.message(F.text.lower() == "получить код")
async def use_code(message: Message, state: FSMContext):
  feedback = get_feedback(message.from_user.id)
  if feedback is not None and feedback.code is not None and feedback.used==0:
    await message.answer(f"Ваш код: {feedback.code}\nСообщите этот код бариста и получите бесплатный напиток!")
  else:
    await message.answer("У вас нет доступного кода!")
