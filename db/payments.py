"""
Оплата размещения бота: каждая строка — срок оплаты за один период.

Текущий срок — последняя строка. Когда администратор отмечает оплату, строка помечается оплаченной
и добавляется новая со следующим сроком, так в таблице остаётся история оплат.
"""
from datetime import date
from config import db_name
from sqlalchemy import Column, Integer, String, Numeric, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from utils.date_utils import now

Base = declarative_base()
engine = create_engine(f'sqlite:///{db_name}')
Session = sessionmaker(bind=engine)

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class Payment(Base):
  __tablename__ = 'payments'
  id = Column(Integer, primary_key=True, autoincrement=True)
  due_date = Column(String, nullable=False)  # ГГГГ-ММ-ДД
  created_at = Column(String, nullable=False)
  paid_at = Column(String)  # None — ещё не оплачено
  paid_by = Column(Numeric)


# Таблицы создаются после объявления моделей, иначе create_all о них не знает
Base.metadata.create_all(engine)


def _get_last(session) -> Payment | None:
  return session.query(Payment).order_by(Payment.id.desc()).first()


def _new_payment(due_date: date) -> Payment:
  return Payment(due_date=due_date.isoformat(), created_at=now().strftime(DATETIME_FORMAT))


def get_payment_date() -> date | None:
  """Возвращает текущий срок оплаты или None, если он не задан."""
  session = Session()
  last = _get_last(session)
  session.close()
  return date.fromisoformat(last.due_date) if last else None


def add_payment_date(due_date: date):
  """Добавляет срок оплаты, он становится текущим."""
  session = Session()
  session.add(_new_payment(due_date))
  session.commit()
  session.close()


def mark_paid(due_date: date, paid_by: int, next_date: date) -> bool:
  """
  Отмечает оплату за срок due_date и добавляет следующий срок next_date.
  Возвращает False, если due_date уже не текущий срок: оплату отметил кто-то другой.
  """
  session = Session()
  last = _get_last(session)
  if last is None or last.due_date != due_date.isoformat() or last.paid_at is not None:
    session.close()
    return False
  last.paid_at = now().strftime(DATETIME_FORMAT)
  last.paid_by = paid_by
  session.add(_new_payment(next_date))
  session.commit()
  session.close()
  return True
