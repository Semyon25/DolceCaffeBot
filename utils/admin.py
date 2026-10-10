from config import admin_ids, manager_ids
from db.users import get_user

def get_admin_ids() -> list[int]:
   return admin_ids

def is_admin(user_id: int) -> bool:
   return int(user_id) in admin_ids

def is_coffeemaker_or_admin(user_id: int) -> bool:
   if is_admin(user_id):
      return True
   user = get_user(user_id)
   return user is not None and user.is_coffeemaker == 1

def get_manager_ids() -> list[int]:
   return manager_ids
