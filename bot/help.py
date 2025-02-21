from aiogram import Bot
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from utils.admin import get_admin_id

router = Router()

@router.message(Command("help"))
async def help(message: Message, bot: Bot):    
  admin_id = int(get_admin_id())
  if message.from_user.id == admin_id:
    await bot.send_message(admin_id, "/approve {userId} - подтвердить ссылку на отзыв для пользователя\n/addNewCoffeemaker {userId} - добавить бариста\n/removeCoffeemaker {userId} - удалить бариста\n/allUsers - список всех пользователей\n/addLink {userId} {link}- добавить ссылку на отзыв\n/broadcast - рассылка всем пользователям\n/sendMessage {userId} - Отправка сообщения пользователю\n/correctPurchaseCount {userId} {count} - Изменение количества накопленных напитков пользователя")