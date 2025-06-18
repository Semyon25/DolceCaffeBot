import os
from dotenv import load_dotenv

load_dotenv()


def require_env(var_name: str) -> str:
  value = os.getenv(var_name)
  if value is None or value.strip() == "":
    raise ValueError(
        f"⛔ Переменная окружения '{var_name}' не установлена в .env")
  return value


db_name = require_env("db_name")
admin_id = require_env("admin_id")
bot_token = require_env("bot_token")
