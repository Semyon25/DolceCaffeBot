import os
from db.users import get_user

def get_admin_id():
   return int(os.environ['admin_id'])

def is_coffeemaker_or_admin(user_id: int) -> bool:
   admin_id = int(os.environ['admin_id'])
   user = get_user(user_id)
   return user_id == admin_id or user.is_coffeemaker == 1
   