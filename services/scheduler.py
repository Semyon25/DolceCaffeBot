import pytz

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bot.planner import plan_next_week, send_planning_reminder
from bot.reminder import send_closing_reminder
from bot.payment_bot import send_payment_reminder

MOSCOW_TZ = pytz.timezone("Europe/Moscow")

class SchedulerService:

    def __init__(self, bot: Bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler(timezone=MOSCOW_TZ)
        self.week_job = None
        self.planning_reminder_job = None
        self.reminder_job = None
        self.payment_job = None

    async def plan_next_week(self):
        await plan_next_week(self.bot)

    async def send_planning_reminder(self):
        await send_planning_reminder(self.bot)

    async def send_reminder(self):
        await send_closing_reminder(self.bot)

    async def send_payment_reminder(self):
        await send_payment_reminder(self.bot)

    def start(self):
        # Планирование следующей недели
        if not self.week_job:
            self.week_job = self.scheduler.add_job(
                self.plan_next_week,
                CronTrigger(
                    day_of_week="fri",
                    hour=15,
                    minute=0,
                    timezone=MOSCOW_TZ
                )
            )
        # Напоминание бариста, которые ещё не выбрали смены на следующую неделю
        if not self.planning_reminder_job:
            self.planning_reminder_job = self.scheduler.add_job(
                self.send_planning_reminder,
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
        # Напоминание администраторам об оплате размещения бота
        if not self.payment_job:
            self.payment_job = self.scheduler.add_job(
                self.send_payment_reminder,
                CronTrigger(
                    hour=12,
                    minute=0,
                    timezone=MOSCOW_TZ
                )
            )
        if not self.scheduler.running:
            self.scheduler.start()

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
        self.week_job = None
        self.planning_reminder_job = None
        self.reminder_job = None
        self.payment_job = None