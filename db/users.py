import os
import datetime
from sqlalchemy import Column, Integer, String, Boolean, Numeric
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

db_name = os.environ['db_name']
Base = declarative_base()
engine = create_engine(f'sqlite:///{db_name}')
Session = sessionmaker(bind=engine)

Base.metadata.create_all(engine)


# Модель
class User(Base):
  __tablename__ = 'users'
  id = Column(Numeric, primary_key=True, unique=True, nullable=False)
  username = Column(String)
  tg_name = Column(String)
  tg_surname = Column(String)
  created_date = Column(String, nullable=False)
  is_coffeemaker = Column(Integer, default=0)


def get_user(user_id):
  session = Session()
  current_user = session.query(User).filter(User.id == user_id).first()
  session.close()
  return current_user


def get_user_by_username(username):
  session = Session()
  current_user = session.query(User).filter(User.username == username).first()
  session.close()
  return current_user


def get_users():
  session = Session()
  users = session.query(User).all()
  session.close()
  return users


def create_user(user_id, username, name, surname):
  now = datetime.datetime.now()
  new_user = User(id=user_id,
                  username=username,
                  tg_name=name,
                  tg_surname=surname,
                  created_date=now.strftime("%d.%m.%Y %H:%M:%S"))
  session = Session()
  session.add(new_user)
  session.commit()
  session.close()


def set_user_as_coffeemaker(user_id):
  session = Session()
  current_user = session.query(User).filter(User.id == user_id).first()
  current_user.is_coffeemaker = 1
  session.commit()
  session.close()
