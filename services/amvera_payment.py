import logging
import aiohttp
import config

# Вход тем же способом, что и официальная утилита amvera (CLI): логин и пароль через Keycloak
TOKEN_URL = "https://id.amvera.ru/auth/realms/amvera/protocol/openid-connect/token"
CLIENT_ID = "amvera-cli"
# Внутренний API личного кабинета Amvera (тот же, что использует cloud.amvera.ru/balance)
API_URL = "https://api.global.amvera.ru"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)
REDIRECT_PREFIX = "redirect:"


class AmveraPaymentError(Exception):
  pass


async def _get_access_token(session: aiohttp.ClientSession) -> str:
  async with session.post(TOKEN_URL, data={"grant_type": "password", "client_id": CLIENT_ID, "scope": "openid",
                                           "username": config.amvera_login, "password": config.amvera_password}) as response:
    data = await response.json(content_type=None)
    token = data.get("access_token") if isinstance(data, dict) else None
    if response.status != 200 or not token:
      # Неверный логин/пароль или вход требует подтверждения
      error = data.get("error_description") or data.get("error") if isinstance(data, dict) else data
      raise AmveraPaymentError(f"вход: HTTP {response.status}, ошибка: {str(error)[:300]}")
    return token


async def create_payment_link() -> str | None:
  """
  Входит в личный кабинет Amvera и создаёт пополнение баланса на сумму payment_amount.
  Возвращает ссылку на оплату (Робокасса) или None, если вход в кабинет не настроен или произошла ошибка.
  """
  if not (config.amvera_login and config.amvera_password and config.payment_amount):
    return None
  try:
    async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
      token = await _get_access_token(session)
      # Карту не сохраняем: оплата разовая, автоплатёж настраивается в кабинете отдельно
      async with session.post(f"{API_URL}/balance/topup",
                              json={"amount": config.payment_amount, "saveCard": False, "cardId": ""},
                              headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}) as response:
        payment = await response.json(content_type=None)
        redirect_url = payment.get("redirectUrl") if isinstance(payment, dict) else None
        if response.status != 200 or not redirect_url:
          raise AmveraPaymentError(f"/balance/topup: HTTP {response.status}, ответ: {str(payment)[:300]}")

      # По redirectUrl кабинет получает текст «redirect:<ссылка на страницу оплаты>»
      async with session.get(redirect_url) as response:
        text = (await response.text()).strip()
        if response.status != 200 or not text.startswith(REDIRECT_PREFIX):
          raise AmveraPaymentError(f"redirectUrl: HTTP {response.status}, ответ: {text[:300]}")
      url = text.removeprefix(REDIRECT_PREFIX).strip()
      if not url.startswith("http"):
        raise AmveraPaymentError(f"redirectUrl: некорректная ссылка: {url[:300]}")
      return url
  except Exception as e:
    logging.error("Не удалось получить ссылку на оплату Amvera: %s", e)
    return None
