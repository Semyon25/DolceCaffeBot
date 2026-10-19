"""
Обновление БД: таблицы расписания смен, которое составляют администраторы.

- schedule_weeks — недели с опубликованным расписанием;
- shift_schedule — опубликованное расписание: кто работает в смену;
- shift_schedule_drafts — правки администраторов, которые ещё не опубликованы.

Перед этим скриптом нужно выполнить 001_shift_wishes.py.
Скрипт можно запускать повторно: существующие таблицы не меняются. Перед изменениями
рядом с файлом БД создаётся резервная копия.

Запуск из корня проекта (путь к БД берётся из .env):
  python migrations/002_shift_schedule.py
или с явным путём к БД:
  python migrations/002_shift_schedule.py path/to/dolce_db.db
"""
from migration_utils import create_tables

TABLES = {
  "schedule_weeks": """
    CREATE TABLE schedule_weeks (
      week_start VARCHAR NOT NULL,
      published_at VARCHAR NOT NULL,
      updated_at VARCHAR NOT NULL,
      PRIMARY KEY (week_start)
    )""",
  "shift_schedule": """
    CREATE TABLE shift_schedule (
      week_start VARCHAR NOT NULL,
      shift VARCHAR NOT NULL,
      user_id NUMERIC NOT NULL,
      PRIMARY KEY (week_start, shift)
    )""",
  "shift_schedule_drafts": """
    CREATE TABLE shift_schedule_drafts (
      week_start VARCHAR NOT NULL,
      shift VARCHAR NOT NULL,
      user_id NUMERIC,
      PRIMARY KEY (week_start, shift)
    )""",
}

# Колонки, которые должны быть в таблицах, — для проверки уже существующих таблиц
COLUMNS = {
  "schedule_weeks": {"week_start", "published_at", "updated_at"},
  "shift_schedule": {"week_start", "shift", "user_id"},
  "shift_schedule_drafts": {"week_start", "shift", "user_id"},
}


if __name__ == "__main__":
  create_tables(TABLES, COLUMNS)
