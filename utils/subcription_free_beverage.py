import datetime
from dateutil.relativedelta import relativedelta
from db.subscriptions import create_subscription, get_active_subscription as get_active_subscription_from_db
from db.subscription_codes import get_unused_code, set_code, set_usage_time, get_last_usage_time, get_user_and_subscription_by_code
from utils.code_generator import generate_code_5
from settings.consts import FREE_BEVERAGE_SUBSCRIOPTION

def create_subscription_period(user_id, start_date, end_date):
  active_subscription = get_active_subscription_from_db(user_id, FREE_BEVERAGE_SUBSCRIOPTION)
  if active_subscription:
      return False  # Уже есть активный абонемент — не создаем новый

  create_subscription(user_id, start_date, end_date, FREE_BEVERAGE_SUBSCRIOPTION)
  return True

def create_monthly_subscription(user_id):
  """Создает абонемент на бесплатный напиток на месяц"""
  start_date = datetime.date.today()
  end_date = start_date + relativedelta(months=1)
  return create_subscription_period(user_id, start_date, end_date)


def create_subscription_until_end_2025(user_id):
  """Создает абонемент на бесплатный напиток до конца 2025 года"""
  start_date = datetime.date.today()
  end_date = datetime.date(2025, 12, 31)
  return create_subscription_period(user_id, start_date, end_date)

def get_active_subscription(user_id):
  """Возвращает активный абонемент на бесплатный напиток, если он есть"""
  return get_active_subscription_from_db(user_id, FREE_BEVERAGE_SUBSCRIOPTION)

def get_unused_code_for_subscription(user_id):
  """Возвращает неиспользованный код для активной подписки пользователя"""
  sub = get_active_subscription(user_id)
  if sub:
    sub_code = get_unused_code(user_id, sub.id)
    if sub_code:
      return sub_code.code
    else:
      new_code = generate_code_5()
      while True:
        u, s = get_user_and_subscription_by_code(new_code)
        if u is None and s is None:
            break  # код уникальный, можно использовать
        new_code = generate_code_5()
      set_code(user_id, sub.id, new_code)
      return new_code
  return None

def use_code_for_subscription(code):
  """Использует код абонемента и возвращает id пользователя и сообщение об ошибке, если она есть"""
  user_id, sub_id = get_user_and_subscription_by_code(code)
  if user_id is not None and sub_id is not None:
    used_at = get_last_usage_time(user_id, sub_id)
    if used_at is None or is_used_before_today(used_at):
      set_usage_time(user_id, sub_id)
      return (user_id, None)
    else:
      return (user_id, f"Код уже использован в {used_at}")
  else:
    return (user_id, "Нет активного абонемента")

def is_used_code_today(user_id):
  """Проверяет, что код был использован сегодня"""
  sub = get_active_subscription(user_id)
  if sub:
    used_at = get_last_usage_time(user_id, sub.id)
    if used_at:
      used_date = datetime.datetime.strptime(used_at, "%d.%m.%Y %H:%M:%S").date()
      today = datetime.date.today()
      print(today)
      return used_date == today
  return False

def is_used_before_today(used_at: str):
  """Проверяет, что дата использования кода меньше текущего дня"""
  try:
      used_date = datetime.datetime.strptime(used_at, "%d.%m.%Y %H:%M:%S").date()
      today = datetime.date.today()
      return used_date < today
  except ValueError:
      return False

def can_buy_subscription_today():
  dates = ["02.11.2025", "04.11.2025"]
  today_str = datetime.date.today().strftime("%d.%m.%Y")
  return today_str in dates