import os

def get_admin_id():
   return os.environ['admin_id']

def is_coffeemaker_or_admin(user_id):
  admin_id = int(os.environ['admin_id'])
  coffeemakers_id = map(int, os.environ["coffeemakers"].split(','))
  return user_id == admin_id or user_id in coffeemakers_id