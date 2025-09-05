import os
from dotenv import load_dotenv

load_dotenv()


def require_env(var_name: str, raise_if_missing: bool = True) -> str | None:
  value = os.getenv(var_name)
  if value is None or value.strip() == "":
      if raise_if_missing:
          raise ValueError(
              f"⛔ Переменная окружения '{var_name}' не установлена в .env"
          )
      return None
  return value


db_name = require_env("db_name")
admin_id = require_env("admin_id")
bot_token = require_env("bot_token")
manager_ids = require_env("manager_ids", raise_if_missing=False)
