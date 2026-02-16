from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from mikroabenteuer.adventure_engine import choose_adventure
from mikroabenteuer.google.gmail_service import send_daily_mail

_scheduler: BackgroundScheduler | None = None


def job() -> None:
    adventure = choose_adventure()
    send_daily_mail(adventure)


def start_scheduler() -> BackgroundScheduler:
    """Start daily background scheduler (08:20 Europe/Berlin)."""
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler

    scheduler = BackgroundScheduler(timezone="Europe/Berlin")
    trigger = CronTrigger(hour=8, minute=20)
    scheduler.add_job(
        job, trigger=trigger, id="daily_adventure_mail", replace_existing=True
    )
    scheduler.start()
    _scheduler = scheduler
    return scheduler
