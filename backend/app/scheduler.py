from apscheduler.schedulers.background import BackgroundScheduler

from .config import settings
from .database import SessionLocal
from .services import pipelines

scheduler = BackgroundScheduler()


def _with_db(fn):
    def runner():
        db = SessionLocal()
        try:
            fn(db)
        finally:
            db.close()
    return runner


def start():
    scheduler.add_job(_with_db(pipelines.email_scan), "cron", hour=settings.daily_email_scan_hour, id="email_scan", replace_existing=True)
    scheduler.add_job(_with_db(pipelines.job_scan), "cron", hour=settings.daily_job_scan_hour, id="job_scan", replace_existing=True)
    scheduler.add_job(_with_db(pipelines.deadline_check), "cron", hour=settings.daily_email_scan_hour, minute=30, id="deadline_check", replace_existing=True)
    scheduler.start()
