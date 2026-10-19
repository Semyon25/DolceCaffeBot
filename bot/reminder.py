from aiogram import Bot
from aiogram.enums import ParseMode
from db.shift_schedule import get_published_schedule
from db.users import get_user
from utils.date_utils import today, get_week_start
from utils.shifts import CLOSING_TIME, get_shift_code
from utils.user_utils import is_coffeemaker


async def send_closing_reminder(bot: Bot):
    """Напоминает бариста вечерней смены из опубликованного расписания ввести остаток в кассе"""
    day = today()
    user_id = get_published_schedule(get_week_start(day)).get(get_shift_code(day, CLOSING_TIME))
    if user_id is None:
        return
    user = get_user(user_id)
    if not is_coffeemaker(user):
        return

    text = "📌 <b>Перед закрытием смены необходимо</b> ввести остаток наличных в кассе в бота"
    await bot.send_message(user_id, text, parse_mode=ParseMode.HTML)
