import pytz

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bot.planner import plan_next_week
from bot.reminder import send_closing_reminder

MOSCOW_TZ = pytz.timezone("Europe/Moscow")

class SchedulerService:

    def __init__(self, bot: Bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler(timezone=MOSCOW_TZ)
        self.week_job = None
        self.reminder_job = None

    async def plan_next_week(self):
        await plan_next_week(self.bot)

    async def send_reminder(self):
        await send_closing_reminder(self.bot)

    def start(self):
        # Планирование следующей недели
        if not self.week_job:
            self.week_job = self.scheduler.add_job(
                self.plan_next_week,
                CronTrigger(
                    day_of_week="sat",
                    hour=15,
                    minute=0,
                    timezone=MOSCOW_TZ
                )
            )
        # Напоминание перед закрытием
        if not self.reminder_job:
            self.reminder_job = self.scheduler.add_job(
                self.send_reminder,
                CronTrigger(
                    hour=21,
                    minute=30,
                    timezone=MOSCOW_TZ
                )
            )
        if not self.scheduler.running:
            self.scheduler.start()

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
        self.week_job = None
        self.reminder_job = None