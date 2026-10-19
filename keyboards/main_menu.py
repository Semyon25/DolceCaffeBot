from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from utils.admin import is_coffeemaker_or_admin, is_admin
from db.feedback import get_feedback
from db.users import get_user
from utils.subcription_free_beverage import can_buy_subscription_today, get_active_subscription
import settings.consts

# Текст кнопки главного меню, открывающей админ-панель
ADMIN_PANEL_BUTTON = "Админ-панель"
# Текст кнопки главного меню бариста для выбора смен на следующую неделю
MY_SHIFTS_BUTTON = "Мои смены"

def get_main_menu(user_id) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()

    # бариста и админ
    if (is_coffeemaker_or_admin(user_id)):
        kb.button(text="Касса")
        kb.button(text="Ввести код")

    # только бариста
    user = get_user(user_id)
    if user is not None and user.is_coffeemaker == 1:
        kb.button(text=MY_SHIFTS_BUTTON)
        
    # kb.button(text="Меню")

    # все кроме бариста
    if (not is_coffeemaker_or_admin(user_id) or is_admin(user_id)):
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
        if can_buy_subscription_today() or get_active_subscription(user_id):
            kb.button(text="Абонемент")

    # только админ
    if is_admin(user_id):
        kb.button(text=ADMIN_PANEL_BUTTON)

    kb.adjust(2) # 2 кнопки в строке
    
    return kb.as_markup(resize_keyboard=True)
