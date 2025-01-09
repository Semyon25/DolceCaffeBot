from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from utils.code_generator import generate_purchase_code_if_needed
from utils.declension_noun import beverage_declension
from db.purchases import get_count, set_count

router = Router()

@router.message(F.text.lower() == "акция 6+1")
async def answer_purchase(message: Message, state: FSMContext):
  user_id = message.from_user.id
  count = get_count(user_id)
  code = generate_purchase_code_if_needed(user_id)
  if count is None:
    await message.answer('''<b>Акция 6+1</b>🎁

После покупки напитка(-ов) нажми на кнопку <b>АКЦИЯ 6+1</b> в чат-боте, получи одноразовый код
Назови этот <b>код</b> бариста 🔢 

Тогда купленные напитки будут накапливаться ☕️☕️☕️☕️☕️☕️
Чат-бот учитывает все напитки в чеке
* кроме воды в бутылках и газировок

Когда накопится шесть напитков, чат-бот отправит <b>купон</b> на <b>седьмой бесплатный напиток</b> 🎁

Чтобы получить новый код для следующей покупки, нажми на кнопку <b>АКЦИЯ 6+1</b> в меню чат-бота'''
                         , parse_mode=ParseMode.HTML) 
    await message.answer(f'<b>Код: {code}</b>\n\nНазови этот код бариста сразу после покупки напитка(-ов) 🧑‍🦰☕️', parse_mode=ParseMode.HTML)
    set_count(user_id, 0)
  elif count >= 0 and count < 6:
    await message.answer(f'Вы накопили <b>{count}</b> {beverage_declension(count)} из 6.\n\n<b>Код: {code}</b>\nНазови этот код бариста сразу после покупки напитка(-ов) 🧑‍🦰☕️', parse_mode=ParseMode.HTML)
  else:
    await message.answer(f'🎉 <b>Поздравляем!</b> 🎉\nВы накопили шесть напитков! Вам доступен <b>бесплатный напиток</b>!☕\nЧтобы получить бесплатный напиток, сообщите бариста код <b>{code}</b>', parse_mode=ParseMode.HTML)
                      
                    