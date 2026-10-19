from utils.background import keep_alive  #импорт функции для поддержки работоспособности
from db.init_db import create_db_if_empty
import asyncio

# Пустая БД создаётся до импорта бота: модули db/ при импорте создают часть таблиц сами,
# и после этого БД уже не считалась бы пустой
create_db_if_empty()

from bot.bot import main

# keep_alive()  #запускаем flask-сервер в отдельном потоке.

asyncio.run(main())
