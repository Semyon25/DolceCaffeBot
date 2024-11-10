from background import keep_alive  #импорт функции для поддержки работоспособности
from bot import main
import asyncio

keep_alive()  #запускаем flask-сервер в отдельном потоке.

asyncio.run(main())