import logging
import aiohttp
import config

# Внутренний API личного кабинета Beget (тот же, что использует cp.beget.com)
API_URL = "https://api-cp.beget.com/v1"
# Константа из кода личного кабинета, без неё запрос авторизации не проходит
AUTH_X_TOKEN = "y0wcxs9n91mxf92"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)
BASE_HEADERS = {
    "accept": "application/json",
    "accept-language": "ru",
    "origin": "https://cp.beget.com",
    "referer": "https://cp.beget.com/",
}


class BegetPaymentError(Exception):
  pass


async def _post(session: aiohttp.ClientSession, path: str, payload: dict, headers: dict) -> dict:
  async with session.post(f"{API_URL}{path}", json=payload, headers={**BASE_HEADERS, **headers}) as response:
    data = await response.json(content_type=None)
    if response.status != 200 or not isinstance(data, dict):
      raise BegetPaymentError(f"{path}: HTTP {response.status}, ответ: {str(data)[:300]}")
    return data


async def create_sbp_payment_link() -> str | None:
  """
  Входит в личный кабинет Beget и создаёт платёж через СБП на сумму payment_amount.
  Возвращает ссылку на QR-код или None, если вход в кабинет не настроен или произошла ошибка.
  """
  if not (config.beget_login and config.beget_password and config.payment_amount):
    return None
  try:
    async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
      auth = await _post(session, "/auth",
                         {"login": config.beget_login, "password": config.beget_password,
                          "code": "", "saveMe": False},
                         {"x-token": AUTH_X_TOKEN})
      token = auth.get("token")
      if not token:
        # В ответе нет токена — неверный логин/пароль или требуется код двухфакторной аутентификации
        raise BegetPaymentError(f"/auth: токен не получен, ошибка: {auth.get('error')}")

      payment = await _post(session, "/payment",
                            {"amount": config.payment_amount, "account_type": "PERSON", "currency": "RUB",
                             "customer_identifier": None, "source": "CP_PAY", "paykeeper_alfa": {}},
                            {"authorization": f"Bearer {token}"})
      url = (payment.get("location") or {}).get("url")
      if not url:
        raise BegetPaymentError(f"/payment: ссылка не получена, ответ: {str(payment)[:300]}")
      return url
  except Exception as e:
    logging.error("Не удалось получить ссылку на оплату Beget: %s", e)
    return None
