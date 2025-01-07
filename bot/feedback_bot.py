from aiogram import Bot
from aiogram.fsm.state import StatesGroup, State
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from db.feedback import get_feedback, update_or_create_feedback
from utils.admin import get_admin_id
from aiogram.enums import ParseMode

router = Router()

class OrderFeedback(StatesGroup):
  waiting_for_link = State()

@router.message(F.text.lower() == "оставить отзыв")
async def answer_feedback(message: Message, state: FSMContext):
    await message.answer("Хочешь **бесплатный** напиток?\nНапиши отзыв на [Яндекс Картах](https://yandex.ru/maps/org/dolce/230301174806/?ll=37.497249%2C55.668364&z=14.52) и отправь ссылку на отзыв в бот⬇️", 
                        parse_mode=ParseMode.MARKDOWN)
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
              f"Обновленная ссылка на отзыв от @{message.from_user.username} ({message.from_user.id}): {link}"
          )
        else:
          await message.answer("Ваша ссылка проходит модерацию. Ожидайте ⏳")
          await bot.send_message(
              admin_id,
              f"Новая ссылка на отзыв от @{message.from_user.username} ({message.from_user.id}): {link}"
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
