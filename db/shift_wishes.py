"""
Пожелания бариста по сменам на неделю.

Неделя определяется датой понедельника (week_start, ГГГГ-ММ-ДД), смена — кодом из utils.shifts ("mon_10_16").
Итоговое расписание, которое администраторы составят по пожеланиям, нужно хранить в отдельной таблице
с теми же ключами: неделя, код смены, бариста.
"""
from dataclasses import dataclass
from datetime import date
from config import db_name
from sqlalchemy import Column, Integer, String, Numeric, UniqueConstraint, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from utils.date_utils import now
from utils.shifts import sort_shifts

Base = declarative_base()
engine = create_engine(f'sqlite:///{db_name}')
Session = sessionmaker(bind=engine)

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class PlanningWeek(Base):
  """Неделя, по которой разослано предложение выбрать смены. Так приём открывают досрочно, до пятницы 15:00"""
  __tablename__ = 'planning_weeks'
  week_start = Column(String, primary_key=True)
  opened_at = Column(String, nullable=False)


class ShiftWishRecord(Base):
  __tablename__ = 'shift_wishes'
  __table_args__ = (UniqueConstraint('week_start', 'user_id'),)
  id = Column(Integer, primary_key=True, autoincrement=True)
  week_start = Column(String, nullable=False)
  user_id = Column(Numeric, nullable=False)
  shifts = Column(String, nullable=False, default='')  # Коды смен через запятую, пустая строка — без смен
  created_at = Column(String, nullable=False)
  updated_at = Column(String, nullable=False)


# Таблицы создаются после объявления моделей, иначе create_all о них не знает
Base.metadata.create_all(engine)


@dataclass
class ShiftWish:
  user_id: int
  shifts: list[str]
  updated_at: str


def split_shifts(value: str | None) -> list[str]:
  return [shift for shift in (value or '').split(',') if shift]


def open_planning_week(week_start: date) -> bool:
  """Отмечает, что приём пожеланий на неделю открыт. Возвращает False, если он уже был открыт."""
  session = Session()
  try:
    if session.get(PlanningWeek, week_start.isoformat()) is not None:
      return False
    session.add(PlanningWeek(week_start=week_start.isoformat(), opened_at=now().strftime(DATETIME_FORMAT)))
    session.commit()
    return True
  finally:
    session.close()


def is_planning_week_opened(week_start: date) -> bool:
  session = Session()
  try:
    return session.get(PlanningWeek, week_start.isoformat()) is not None
  finally:
    session.close()


def get_shift_wish(week_start: date, user_id) -> list[str] | None:
  """Смены, которые бариста отправил на неделю. None — бариста ещё ничего не отправлял."""
  session = Session()
  try:
    record = session.query(ShiftWishRecord).filter(ShiftWishRecord.week_start == week_start.isoformat(),
                                                   ShiftWishRecord.user_id == user_id).first()
    return split_shifts(record.shifts) if record else None
  finally:
    session.close()


def save_shift_wish(week_start: date, user_id, shifts: list[str]) -> list[str] | None:
  """Сохраняет выбор бариста на неделю. Возвращает предыдущий выбор или None, если выбор первый."""
  session = Session()
  try:
    timestamp = now().strftime(DATETIME_FORMAT)
    record = session.query(ShiftWishRecord).filter(ShiftWishRecord.week_start == week_start.isoformat(),
                                                   ShiftWishRecord.user_id == user_id).first()
    previous = split_shifts(record.shifts) if record else None
    if record is None:
      record = ShiftWishRecord(week_start=week_start.isoformat(), user_id=user_id, created_at=timestamp)
      session.add(record)
    record.shifts = ','.join(sort_shifts(shifts))
    record.updated_at = timestamp
    session.commit()
    return previous
  finally:
    session.close()


def get_shift_wishes(week_start: date) -> list[ShiftWish]:
  """Все пожелания на неделю"""
  session = Session()
  try:
    records = session.query(ShiftWishRecord).filter(ShiftWishRecord.week_start == week_start.isoformat()).all()
    return [ShiftWish(int(record.user_id), split_shifts(record.shifts), record.updated_at) for record in records]
  finally:
    session.close()
