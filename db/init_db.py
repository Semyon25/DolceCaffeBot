"""
Создание БД бота с нуля: все таблицы в актуальном виде.

Выполняется автоматически при запуске бота (main.py), если в БД нет ни одной таблицы
или файла БД ещё нет. Существующую БД не меняет.
При добавлении таблицы её нужно описать здесь, а в работающую БД добавить отдельно.

Ручной запуск из корня проекта: python -m db.init_db
"""
import sqlite3
from pathlib import Path
from config import db_name

TABLES = [
  # Пользователи и акции
  """CREATE TABLE "users" (
    "id" NUMERIC NOT NULL UNIQUE,
    "username" TEXT,
    "tg_name" TEXT,
    "tg_surname" TEXT,
    "created_date" TEXT NOT NULL,
    "is_coffeemaker" INTEGER,
    "name" TEXT,
    PRIMARY KEY("id")
  )""",
  """CREATE TABLE "feedback" (
    "user_id" NUMERIC NOT NULL UNIQUE,
    "link" TEXT,
    "code" TEXT,
    "used" INTEGER,
    PRIMARY KEY("user_id")
  )""",
  """CREATE TABLE "purchases" (
    "user_id" NUMERIC NOT NULL UNIQUE,
    "count" INTEGER,
    PRIMARY KEY("user_id")
  )""",
  """CREATE TABLE "codes" (
    "id" INTEGER NOT NULL DEFAULT 0,
    "user_id" NUMERIC NOT NULL,
    "code" TEXT NOT NULL,
    "is_used" INTEGER,
    PRIMARY KEY("id" AUTOINCREMENT)
  )""",
  """CREATE TABLE "subscriptions" (
    "id" INTEGER,
    "user_id" NUMERIC NOT NULL UNIQUE,
    "start_date" TEXT NOT NULL,
    "end_date" TEXT NOT NULL,
    "sub_name" TEXT NOT NULL,
    PRIMARY KEY("id" AUTOINCREMENT)
  )""",
  """CREATE TABLE "subscription_codes" (
    "id" INTEGER,
    "user_id" NUMERIC NOT NULL,
    "subscription_id" INTEGER NOT NULL,
    "code" TEXT NOT NULL,
    "used_at" TEXT,
    PRIMARY KEY("id" AUTOINCREMENT)
  )""",
  # Пожелания бариста по сменам
  """CREATE TABLE planning_weeks (
    week_start VARCHAR NOT NULL,
    opened_at VARCHAR NOT NULL,
    PRIMARY KEY (week_start)
  )""",
  """CREATE TABLE shift_wishes (
    id INTEGER NOT NULL,
    week_start VARCHAR NOT NULL,
    user_id NUMERIC NOT NULL,
    shifts VARCHAR NOT NULL,
    created_at VARCHAR NOT NULL,
    updated_at VARCHAR NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (week_start, user_id)
  )""",
  # Расписание смен
  """CREATE TABLE schedule_weeks (
    week_start VARCHAR NOT NULL,
    published_at VARCHAR NOT NULL,
    updated_at VARCHAR NOT NULL,
    PRIMARY KEY (week_start)
  )""",
  """CREATE TABLE shift_schedule (
    week_start VARCHAR NOT NULL,
    shift VARCHAR NOT NULL,
    user_id NUMERIC NOT NULL,
    PRIMARY KEY (week_start, shift)
  )""",
  """CREATE TABLE shift_schedule_drafts (
    week_start VARCHAR NOT NULL,
    shift VARCHAR NOT NULL,
    user_id NUMERIC,
    PRIMARY KEY (week_start, shift)
  )""",
]


def create_db_if_empty() -> bool:
  """Создаёт все таблицы, если в БД нет ни одной. Возвращает True, если БД создана."""
  db_path = Path(db_name)
  db_path.parent.mkdir(parents=True, exist_ok=True)
  connection = sqlite3.connect(db_path)
  try:
    tables = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'").fetchall()
    if tables:
      return False
    # Все таблицы создаются в одной транзакции: либо все, либо ни одной.
    # sqlite3 сам не открывает транзакцию перед CREATE TABLE, поэтому BEGIN явный
    connection.execute("BEGIN")
    try:
      for table in TABLES:
        connection.execute(table)
      connection.commit()
    except Exception:
      connection.rollback()
      raise
  finally:
    connection.close()
  # flush: сообщение должно попасть в лог сразу, даже если бот потом упадёт
  print(f"✅ Создана новая БД '{db_path}'", flush=True)
  return True


if __name__ == "__main__":
  if not create_db_if_empty():
    print(f"БД '{db_name}' уже содержит таблицы, изменений нет")
