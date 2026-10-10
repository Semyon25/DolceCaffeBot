from pathlib import Path
from dotenv import dotenv_values, set_key

# Все секреты читаются только из файла, переменные окружения игнорируются
SECRETS_FILE = Path(__file__).resolve().parent / ".env"

if not SECRETS_FILE.exists():
  raise FileNotFoundError(f"⛔ Файл с секретами '{SECRETS_FILE}' не найден")

_secrets = dotenv_values(SECRETS_FILE)


def require_secret(var_name: str, raise_if_missing: bool = True) -> str | None:
  value = _secrets.get(var_name)
  if value is None or value.strip() == "":
      if raise_if_missing:
          raise ValueError(
              f"⛔ Параметр '{var_name}' не задан в файле {SECRETS_FILE.name}"
          )
      return None
  return value.strip()


def parse_ids(value: str | None) -> list[int]:
  if value is None:
    return []
  return [int(x) for x in value.split(';') if x.strip()]


db_name = require_secret("db_name")
admin_ids = parse_ids(require_secret("admin_ids"))
bot_token = require_secret("bot_token")
manager_ids = parse_ids(require_secret("manager_ids", raise_if_missing=False))
schedule_file = require_secret("schedule_file", raise_if_missing=False)


def save_admin_ids(ids: list[int]):
  """
  Записывает список администраторов в файл с секретами и обновляет его в памяти.
  """
  set_key(SECRETS_FILE, "admin_ids", ";".join(str(x) for x in ids), quote_mode="never")
  # Меняем список на месте, чтобы изменения увидели все модули, импортировавшие admin_ids
  admin_ids[:] = ids
