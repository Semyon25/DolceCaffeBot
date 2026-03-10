from datetime import datetime
from aiogram import Bot
from services.schedule_storage import load_schedule
from db.users import get_user_by_name

async def send_closing_reminder(bot: Bot):

    schedule = load_schedule()
    today = datetime.now().date()
    employee = schedule.get(today)
    if not employee:
        return
        
    employee_name = str(employee).strip()
    user = get_user_by_name(employee_name)
    if not user:
        return
        
    text = (
        "📌 *Перед закрытием кассы необходимо:*\n\n"
        "1. Ввести остаток наличных в кассе в бота\n"
        "2. Пересчитать конфеты:\n"
        "   - Левушка (Kinder) — по количеству полосок\n"
        "   - Шоко Кроко (Kinder Country) — по количеству пластин\n\n"
        "После подсчёта отправьте результаты в этот бот."
    )
    await bot.send_message(user.id, text)