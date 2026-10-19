"""
Обновление БД: таблицы для планирования смен бариста.

- planning_weeks — недели, по которым разослано предложение выбрать смены (досрочное открытие приёма);
- shift_wishes — пожелания бариста по сменам на неделю.

Скрипт можно запускать повторно: существующие таблицы не меняются. Перед изменениями
рядом с файлом БД создаётся резервная копия.

Запуск из корня проекта (путь к БД берётся из .env):
  python migrations/001_shift_wishes.py
или с явным путём к БД:
  python migrations/001_shift_wishes.py path/to/dolce_db.db
"""
from migration_utils import create_tables

TABLES = {
  "planning_weeks": """
    CREATE TABLE planning_weeks (
      week_start VARCHAR NOT NULL,
      opened_at VARCHAR NOT NULL,
      PRIMARY KEY (week_start)
    )""",
  "shift_wishes": """
    CREATE TABLE shift_wishes (
      id INTEGER NOT NULL,
      week_start VARCHAR NOT NULL,
      user_id NUMERIC NOT NULL,
      shifts VARCHAR NOT NULL,
      created_at VARCHAR NOT NULL,
      updated_at VARCHAR NOT NULL,
      PRIMARY KEY (id),
      UNIQUE (week_start, user_id)
    )""",
}

# Колонки, которые должны быть в таблицах, — для проверки уже существующих таблиц
COLUMNS = {
  "planning_weeks": {"week_start", "opened_at"},
  "shift_wishes": {"id", "week_start", "user_id", "shifts", "created_at", "updated_at"},
}


if __name__ == "__main__":
  create_tables(TABLES, COLUMNS)
