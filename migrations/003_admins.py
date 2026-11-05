"""
Обновление БД: перенос администраторов из старого параметра admin_ids (.env или переменная окружения) в таблицу admins.

Перед запуском в .env нужно указать main_admin_id — главного администратора. Он в таблицу не попадает.
Таблица admins создаётся автоматически. Скрипт можно запускать повторно: уже перенесённые администраторы пропускаются.
После переноса параметр admin_ids из .env можно удалить.

Запуск из корня проекта:
  python migrations/003_admins.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import main_admin_id, parse_ids, require_secret
import db.admins as admins_db


if __name__ == "__main__":
  old_ids = parse_ids(require_secret("admin_ids", raise_if_missing=False))
  if not old_ids:
    sys.exit("⛔ Параметр admin_ids не задан, переносить нечего")

  for user_id in old_ids:
    if user_id == main_admin_id:
      print(f"✔ {user_id} — главный администратор, в таблицу не переносится")
    elif admins_db.add_admin(user_id, added_by=None):
      print(f"✅ {user_id} перенесён")
    else:
      print(f"✔ {user_id} уже в таблице")
  print("Готово")
