from config import admin_id, manager_ids
from db.users import get_user

def get_admin_id():
   return int(admin_id)

def is_coffeemaker_or_admin(user_id: int) -> bool:
   admin_id = get_admin_id()
   user = get_user(user_id)
   return user_id == admin_id or user.is_coffeemaker == 1

def get_manager_ids() -> list[int]:
   if manager_ids is None:
      return []
   return [int(x) for x in manager_ids.split(';') if x.strip()]

