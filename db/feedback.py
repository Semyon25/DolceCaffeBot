import os
from sqlalchemy import Column, Numeric, String, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

db_name = os.environ['db_name']
Base = declarative_base()
engine = create_engine(f'sqlite:///{db_name}')
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

# Модель
class Feedback(Base):
  __tablename__ = 'feedback'
  user_id = Column(Numeric, primary_key=True, unique=True, nullable=False)
  link = Column(String, default=None)
  code = Column(String, default=None)
  used = Column(Integer, default=0)


# Функция для получения отзыва по ID пользователя
def get_feedback(user_id):
  session = Session()
  feedback = session.query(Feedback).filter(Feedback.user_id == user_id).first()
  session.close()
  return feedback

# Функция для обновления или создания записи отзыва
def update_or_create_feedback(user_id, link):
  session = Session()
  existing_feedback = session.query(Feedback).filter(
      Feedback.user_id == user_id, Feedback.code.is_(None)).first()
  if existing_feedback:
    existing_feedback.link = link
    session.commit()
    session.close()
    return True, existing_feedback
  else:
    feedback = Feedback(user_id=user_id, link=link, code=None, used=0)
    session.add(feedback)
    session.commit()
    session.close()
    return False, feedback


# Функция для обновления кода отзыва
def update_feedback_code(user_id, code):
  session = Session()
  feedback = session.query(Feedback).filter(Feedback.user_id == user_id).first()
  if feedback:
    feedback.code = code
    session.commit()
  session.close()


# Функция для подтверждения использования кода
def confirm_code_usage(code):
  session = Session()
  feedback = session.query(Feedback).filter(Feedback.code == code, Feedback.used == 0).first()
  confirm = feedback is not None
  user_id = None
  if feedback:
    user_id = feedback.user_id
    feedback.used = 1
    session.commit()
  session.close()
  return confirm, user_id

def check_if_code_unique(code):
  session = Session()
  feedback = session.query(Feedback).filter(Feedback.code == code).first()
  if feedback:
    return False
  return True

