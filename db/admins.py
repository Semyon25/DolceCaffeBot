"""
Администраторы, назначенные в боте.

Главный администратор задаётся в .env (main_admin_id) и в этой таблице не хранится.
"""
from config import db_name
from sqlalchemy import Column, String, Numeric, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from utils.date_utils import now

Base = declarative_base()
engine = create_engine(f'sqlite:///{db_name}')
Session = sessionmaker(bind=engine)

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class Admin(Base):
  __tablename__ = 'admins'
  user_id = Column(Numeric, primary_key=True)
  added_by = Column(Numeric)  # Кто назначил, None — перенесён из .env
  added_at = Column(String, nullable=False)


# Таблицы создаются после объявления моделей, иначе create_all о них не знает
Base.metadata.create_all(engine)


def get_admin_ids() -> list[int]:
  """Возвращает id администраторов в порядке назначения."""
  session = Session()
  admins = session.query(Admin).order_by(Admin.added_at).all()
  session.close()
  return [int(admin.user_id) for admin in admins]


def is_admin(user_id: int) -> bool:
  session = Session()
  admin = session.query(Admin).filter(Admin.user_id == user_id).first()
  session.close()
  return admin is not None


def add_admin(user_id: int, added_by: int | None) -> bool:
  """Добавляет администратора. Возвращает False, если он уже есть."""
  session = Session()
  if session.query(Admin).filter(Admin.user_id == user_id).first() is not None:
    session.close()
    return False
  session.add(Admin(user_id=user_id, added_by=added_by, added_at=now().strftime(DATETIME_FORMAT)))
  session.commit()
  session.close()
  return True


def remove_admin(user_id: int) -> bool:
  """Удаляет администратора. Возвращает False, если его нет."""
  session = Session()
  deleted = session.query(Admin).filter(Admin.user_id == user_id).delete()
  session.commit()
  session.close()
  return deleted > 0
