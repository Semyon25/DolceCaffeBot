from db.users import User
from db.feedback import Feedback

def get_user_name(user: User):
  if user.username is not None:
    return f"@{user.username}"
  elif user.tg_name is not None:
    return user.tg_name
  elif user.tg_surname is not None:
      return user.tg_surname
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
    return '🔒'
  elif feedback.code is not None and feedback.used == 0:
    return '⏳'
  elif feedback.used != 0:
    return '✅'
  