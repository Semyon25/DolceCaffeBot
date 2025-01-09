from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from utils.admin import is_coffeemaker_or_admin
from db.feedback import get_feedback
import settings.consts

def get_main_menu(user_id) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    
    if (is_coffeemaker_or_admin(user_id)):
        kb.button(text="Ввести код")
        
    # kb.button(text="Меню")
    
    if settings.consts.FEEDBACK_MODE:
        feedback = get_feedback(user_id)
        was_used = 0
        code = None
        if feedback:
            was_used = feedback.used
            code = feedback.code
        if code is None:
            kb.button(text="Оставить отзыв")
        if code is not None and was_used == 0:
            kb.button(text="Получить код")

    if settings.consts.PURCHASE_MODE:
        kb.button(text="Акция 6+1")
            
    return kb.as_markup(resize_keyboard=True)
