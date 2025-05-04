import random 
from db.codes import get_code_4, check_if_code_unique, set_code

# Функция для генерации кода
def generate_code_6():
  return str(random.randint(100000, 999999))

def generate_code_4():
  return str(random.randint(1000, 9999))

def generate_purchase_code_if_needed(user_id):
  code = get_code_4(user_id)
  if code is None:
    code = generate_code_4()
    while not check_if_code_unique(code):
      code = generate_code_4()
    set_code(user_id, code)
  return code