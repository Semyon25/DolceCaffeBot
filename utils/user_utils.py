from db.users import User
from db.feedback import Feedback

def get_user_name(user: User):
  answer = ''
  if user is None:
    return answer
  if user.username is not None:
    answer += f"@{user.username} "
  if user.tg_name is not None:
    answer += f"{user.tg_name} "
  if user.tg_surname is not None:
    answer += f"{user.tg_surname}"
  if answer != '':
    return answer
  else:
    return str(user.id)

def get_coffeemaker_emoji(user: User):
  if user.is_coffeemaker != 0:
    return '☕'
  else:
    return ''

def get_feedback_emoji(feedback: Feedback):
  if feedback is None or feedback.link is None:
    return ''
  elif feedback.link is not None and feedback.code is None:
    return '⏳'
  elif feedback.code is not None and feedback.used == 0:
    return '✔'
  elif feedback.used != 0:
    return '✅'

def get_beverage_count_emoji(count):
  if count == 0:
    return ''
  else f'☕{count}'
