from config import main_admin_id
import db.admins as admins_db
from db.users import get_user

def get_admin_ids() -> list[int]:
   """
   Возвращает id всех администраторов: первым главный из .env, затем назначенные в боте.
   """
   return [main_admin_id] + [x for x in admins_db.get_admin_ids() if x != main_admin_id]

def is_main_admin(user_id: int) -> bool:
   return int(user_id) == main_admin_id

def is_admin(user_id: int) -> bool:
   return is_main_admin(user_id) or admins_db.is_admin(int(user_id))

def add_admin(user_id: int, added_by: int | None = None) -> bool:
   """
   Добавляет администратора в БД. Возвращает False, если он уже администратор.
   """
   if is_admin(user_id):
      return False
   return admins_db.add_admin(int(user_id), added_by)

def remove_admin(user_id: int) -> bool:
   """
   Удаляет администратора из БД. Возвращает False, если он не администратор или это главный администратор.
   """
   if is_main_admin(user_id):
      return False
   return admins_db.remove_admin(int(user_id))

def is_coffeemaker_or_admin(user_id: int) -> bool:
   if is_admin(user_id):
      return True
   user = get_user(user_id)
   return user is not None and user.is_coffeemaker == 1
