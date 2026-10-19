"""
Расписание смен, которое составляют администраторы.

Неделя определяется датой понедельника (week_start, ГГГГ-ММ-ДД), смена — кодом из utils.shifts ("mon_10_16").
На смену назначается один бариста. Опубликованное расписание видят бариста, правки администраторов
до публикации хранятся отдельно, в черновике.
"""
from dataclasses import dataclass
from datetime import date
from config import db_name
from sqlalchemy import Column, String, Numeric, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from utils.date_utils import now

Base = declarative_base()
engine = create_engine(f'sqlite:///{db_name}')
Session = sessionmaker(bind=engine)

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class ScheduleWeek(Base):
  """Неделя с опубликованным расписанием"""
  __tablename__ = 'schedule_weeks'
  week_start = Column(String, primary_key=True)
  published_at = Column(String, nullable=False)  # Первая публикация
  updated_at = Column(String, nullable=False)  # Последняя публикация изменений


class ShiftAssignment(Base):
  """Опубликованное расписание: бариста на смене. Смены без бариста не хранятся."""
  __tablename__ = 'shift_schedule'
  week_start = Column(String, primary_key=True)
  shift = Column(String, primary_key=True)
  user_id = Column(Numeric, nullable=False)


class ShiftAssignmentDraft(Base):
  """Неопубликованная правка администратора. user_id NULL — на смену явно никого не ставят."""
  __tablename__ = 'shift_schedule_drafts'
  week_start = Column(String, primary_key=True)
  shift = Column(String, primary_key=True)
  user_id = Column(Numeric, nullable=True)


# Таблицы создаются после объявления моделей, иначе create_all о них не знает
Base.metadata.create_all(engine)


@dataclass
class PublishedWeek:
  published_at: str
  updated_at: str


def get_published_week(week_start: date) -> PublishedWeek | None:
  """Когда расписание на неделю опубликовали. None — ещё не публиковали."""
  session = Session()
  try:
    week = session.get(ScheduleWeek, week_start.isoformat())
    return PublishedWeek(week.published_at, week.updated_at) if week else None
  finally:
    session.close()


def is_schedule_published(week_start: date) -> bool:
  return get_published_week(week_start) is not None


def get_published_schedule(week_start: date) -> dict[str, int]:
  """Опубликованное расписание: смена -> бариста"""
  session = Session()
  try:
    rows = session.query(ShiftAssignment).filter(ShiftAssignment.week_start == week_start.isoformat()).all()
    return {row.shift: int(row.user_id) for row in rows}
  finally:
    session.close()


def get_schedule_drafts(week_start: date) -> dict[str, int | None]:
  """Неопубликованные правки: смена -> бариста (None — никого)"""
  session = Session()
  try:
    rows = session.query(ShiftAssignmentDraft).filter(ShiftAssignmentDraft.week_start == week_start.isoformat()).all()
    return {row.shift: int(row.user_id) if row.user_id is not None else None for row in rows}
  finally:
    session.close()


def set_schedule_draft(week_start: date, shift: str, user_id: int | None):
  session = Session()
  try:
    session.merge(ShiftAssignmentDraft(week_start=week_start.isoformat(), shift=shift, user_id=user_id))
    session.commit()
  finally:
    session.close()


def remove_schedule_draft(week_start: date, shift: str):
  session = Session()
  try:
    session.query(ShiftAssignmentDraft).filter(ShiftAssignmentDraft.week_start == week_start.isoformat(),
                                               ShiftAssignmentDraft.shift == shift).delete()
    session.commit()
  finally:
    session.close()


def clear_schedule_drafts(week_start: date):
  session = Session()
  try:
    session.query(ShiftAssignmentDraft).filter(ShiftAssignmentDraft.week_start == week_start.isoformat()).delete()
    session.commit()
  finally:
    session.close()


def publish_schedule(week_start: date, schedule: dict[str, int | None]):
  """Сохраняет расписание недели как опубликованное и очищает черновик"""
  week = week_start.isoformat()
  timestamp = now().strftime(DATETIME_FORMAT)
  session = Session()
  try:
    session.query(ShiftAssignment).filter(ShiftAssignment.week_start == week).delete()
    for shift, user_id in schedule.items():
      if user_id is not None:
        session.add(ShiftAssignment(week_start=week, shift=shift, user_id=user_id))
    session.query(ShiftAssignmentDraft).filter(ShiftAssignmentDraft.week_start == week).delete()
    published = session.get(ScheduleWeek, week)
    if published is None:
      session.add(ScheduleWeek(week_start=week, published_at=timestamp, updated_at=timestamp))
    else:
      published.updated_at = timestamp
    session.commit()
  finally:
    session.close()
