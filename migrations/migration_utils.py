"""
Общая часть скриптов обновления БД: создание недостающих таблиц с резервной копией.

Путь к БД берётся из первого аргумента командной строки или из .env, как у бота.
"""
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


def get_db_path() -> Path:
  if len(sys.argv) > 1:
    return Path(sys.argv[1])
  # Путь к БД из .env, как у бота
  sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
  from config import db_name
  return Path(db_name)


def get_columns(connection: sqlite3.Connection, table: str) -> set[str]:
  return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def create_tables(tables: dict[str, str], columns: dict[str, set[str]]):
  """
  Создаёт таблицы, которых ещё нет в БД. tables — имя таблицы -> CREATE TABLE,
  columns — имя таблицы -> колонки, которые должны быть у уже существующей таблицы.
  Существующие таблицы не меняются. Перед изменениями рядом с файлом БД создаётся резервная копия.
  """
  db_path = get_db_path()
  if not db_path.exists():
    sys.exit(f"⛔ Файл БД '{db_path}' не найден")

  connection = sqlite3.connect(db_path)
  try:
    existing = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    missing = [table for table in tables if table not in existing]

    for table in tables:
      if table in existing:
        lost = columns[table] - get_columns(connection, table)
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
        connection.execute(tables[table])
      connection.commit()
    except Exception:
      connection.rollback()
      raise
    for table in missing:
      print(f"✅ Создана таблица {table}")
  finally:
    connection.close()

  print("Готово")
