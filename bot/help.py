from aiogram import Bot
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from utils.admin import is_admin

router = Router()

@router.message(Command("help"))
async def help(message: Message, bot: Bot):    
  if is_admin(message.from_user.id):
    await message.answer("/admin - админ-панель на кнопках (или кнопка «Админ-панель» в меню)\n\n/allUsers - список всех бариста\n/allUsersInDetails - список всех пользователей\n/addNewCoffeemaker {userId} [{name}]- добавить бариста\n/removeCoffeemaker {userId} - удалить бариста\n/planNextWeek - отправка сообщения бариста о планировании следующей недели\n/shiftWishes - пожелания бариста по сменам\n/paymentLink - получить ссылку СБП на оплату размещения бота\n/broadcast - рассылка всем пользователям\n/sendMessage {userId} - Отправка сообщения пользователю\n/correctPurchaseCount {userId} {count} - Изменение количества накопленных напитков пользователя\n/admins - список администраторов\n/addAdmin {userId} - добавить администратора\n/removeAdmin {userId} - удалить администратора")

    #\n/addNewCode {code} - Добавление 8-значного кода в базу\n/approve {userId} - подтвердить ссылку на отзыв для пользователя\n/addLink {userId} {link}- добавить ссылку на отзыв\n/add_subscription {userId} - добавить абонемент пользователю