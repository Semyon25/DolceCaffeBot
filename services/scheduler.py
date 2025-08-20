from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from aiogram import Bot
from bot.planner import plan_next_week

MOSCOW_TZ = pytz.timezone("Europe/Moscow")

class SchedulerService:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler(timezone=MOSCOW_TZ)
        self.job = None

    async def plan_next_week(self):
        await plan_next_week(self.bot)

    def start(self):
        if not self.job:
            # Добавляем задачу: каждую субботу в 15:00
            self.job = self.scheduler.add_job(
                self.plan_next_week,
                # CronTrigger(second=0, timezone=MOSCOW_TZ)  # for testing
                CronTrigger(day_of_week="sat", hour=15, minute=0, timezone=MOSCOW_TZ)
            )
        if not self.scheduler.running:
            self.scheduler.start()

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
        self.job = None
