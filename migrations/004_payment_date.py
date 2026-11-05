"""
Обновление БД: перенос срока оплаты размещения бота из параметра payment_date (.env или переменная окружения)
в таблицу payments. Таблица создаётся автоматически.

Срок добавляется, только если таблица пустая, поэтому скрипт можно запускать повторно.
После переноса параметр payment_date из .env можно удалить.

Запуск из корня проекта (срок из payment_date):
  python migrations/004_payment_date.py
или с явным сроком, например для новой БД:
  python migrations/004_payment_date.py 17.10.2026
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import require_secret
from db.init_db import create_db_if_empty

# Новая БД создаётся до импорта db.payments, как в main.py: иначе она уже не считалась бы пустой
create_db_if_empty()

from db.payments import get_payment_date, add_payment_date

PAYMENT_DATE_FORMAT = "%d.%m.%Y"


if __name__ == "__main__":
  current = get_payment_date()
  if current is not None:
    sys.exit(f"✔ Срок оплаты уже есть в БД: {current.strftime(PAYMENT_DATE_FORMAT)}, изменений нет")

  value = sys.argv[1] if len(sys.argv) > 1 else require_secret("payment_date", raise_if_missing=False)
  if not value:
    sys.exit("⛔ Параметр payment_date не задан, укажите срок оплаты аргументом: ДД.ММ.ГГГГ")

  due_date = datetime.strptime(value, PAYMENT_DATE_FORMAT).date()
  add_payment_date(due_date)
  print(f"✅ Срок оплаты {due_date.strftime(PAYMENT_DATE_FORMAT)} добавлен в БД")
