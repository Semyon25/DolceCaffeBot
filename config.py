import os
from pathlib import Path
from dotenv import dotenv_values

# Секреты ищутся сначала в файле .env, а если файла или параметра в нём нет — в переменных окружения
SECRETS_FILE = Path(__file__).resolve().parent / ".env"

_secrets = dotenv_values(SECRETS_FILE) if SECRETS_FILE.exists() else {}


def _get_secret(var_name: str) -> str | None:
  for value in (_secrets.get(var_name), os.environ.get(var_name)):
    if value is not None and value.strip() != "":
      return value.strip()
  return None


def require_secret(var_name: str, raise_if_missing: bool = True) -> str | None:
  value = _get_secret(var_name)
  if value is None and raise_if_missing:
    raise ValueError(
        f"⛔ Параметр '{var_name}' не задан ни в файле {SECRETS_FILE.name}, ни в переменных окружения"
    )
  return value


def parse_ids(value: str | None) -> list[int]:
  if value is None:
    return []
  return [int(x) for x in value.split(';') if x.strip()]


db_name = require_secret("db_name")
# Главный администратор: назначает остальных, снять с него роль нельзя. Остальные хранятся в БД (db/admins.py)
main_admin_id = int(require_secret("main_admin_id"))
bot_token = require_secret("bot_token")

# Оплата размещения бота (срок оплаты хранится в БД, db/payments.py).
# Вход в личный кабинет Beget и сумма платежа — для получения новой ссылки СБП при каждом напоминании
beget_login = require_secret("beget_login", raise_if_missing=False)
beget_password = require_secret("beget_password", raise_if_missing=False)
_payment_amount = require_secret("payment_amount", raise_if_missing=False)
payment_amount = int(_payment_amount) if _payment_amount else None
