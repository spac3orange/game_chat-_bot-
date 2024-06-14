import asyncio
import random
from config import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from handlers.reviews import send_rev_notif
from datetime import datetime, timedelta


class Scheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    async def schedule_review(self, timing, message, g_id):
        run_time = datetime.now() + timedelta(seconds=timing)
        self.scheduler.add_job(send_rev_notif, 'date', run_date=run_time, args=(message, g_id))
        self.scheduler.start()
        logger.info(f"Task scheduled to run at {run_time}")


