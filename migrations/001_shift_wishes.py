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
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

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


def get_db_path() -> Path:
  if len(sys.argv) > 1:
    return Path(sys.argv[1])
  # Путь к БД из .env, как у бота
  sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
  from config import db_name
  return Path(db_name)


def get_columns(connection: sqlite3.Connection, table: str) -> set[str]:
  return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def main():
  db_path = get_db_path()
  if not db_path.exists():
    sys.exit(f"⛔ Файл БД '{db_path}' не найден")

  connection = sqlite3.connect(db_path)
  try:
    existing = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    missing = [table for table in TABLES if table not in existing]

    for table in TABLES:
      if table in existing:
        lost = COLUMNS[table] - get_columns(connection, table)
        if lost:
          sys.exit(f"⛔ В таблице {table} нет колонок: {', '.join(sorted(lost))}. Обновите таблицу вручную")
        print(f"✔ Таблица {table} уже есть")

    if not missing:
      print("БД уже обновлена, изменений нет")
      return

    backup_path = db_path.with_name(f"{db_path.name}.bak-{datetime.now():%Y%m%d-%H%M%S}")
    shutil.copy2(db_path, backup_path)
    print(f"💾 Резервная копия: {backup_path}")

    # Все таблицы создаются в одной транзакции: либо все, либо ни одной.
    # sqlite3 сам не открывает транзакцию перед CREATE TABLE, поэтому BEGIN явный
    connection.execute("BEGIN")
    try:
      for table in missing:
        connection.execute(TABLES[table])
      connection.commit()
    except Exception:
      connection.rollback()
      raise
    for table in missing:
      print(f"✅ Создана таблица {table}")
  finally:
    connection.close()

  print("Готово")


if __name__ == "__main__":
  main()
