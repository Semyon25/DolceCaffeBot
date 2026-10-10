from config import admin_ids, manager_ids, save_admin_ids
from db.users import get_user

def get_admin_ids() -> list[int]:
   return admin_ids

def is_admin(user_id: int) -> bool:
   return int(user_id) in admin_ids

def add_admin(user_id: int) -> bool:
   """
   Добавляет администратора в файл настроек. Возвращает False, если он уже администратор.
   """
   if is_admin(user_id):
      return False
   save_admin_ids(admin_ids + [int(user_id)])
   return True

def remove_admin(user_id: int) -> bool:
   """
   Удаляет администратора из файла настроек. Возвращает False, если он не администратор.
   """
   if not is_admin(user_id):
      return False
   save_admin_ids([x for x in admin_ids if x != int(user_id)])
   return True

def is_coffeemaker_or_admin(user_id: int) -> bool:
   if is_admin(user_id):
      return True
   user = get_user(user_id)
   return user is not None and user.is_coffeemaker == 1

def get_manager_ids() -> list[int]:
   return manager_ids
