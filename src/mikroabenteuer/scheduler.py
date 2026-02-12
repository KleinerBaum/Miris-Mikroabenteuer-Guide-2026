# src/mikroabenteuer/scheduler.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .config import AppConfig
from .data_seed import seed_adventures
from .email_templates import render_daily_email_html
from .ics import build_ics_event
from .models import ActivitySearchCriteria
from .openai_gen import generate_daily_markdown
from .recommender import pick_daily_adventure
from .weather import fetch_weather_for_day


@dataclass(frozen=True)
class DailyJobResult:
    subject: str
    to_email: str
    adventure_slug: str


def run_daily_job_once(
    cfg: AppConfig,
    criteria: ActivitySearchCriteria,
    *,
    send_email: bool = False,
    create_calendar_event: bool = False,
) -> DailyJobResult:
    """
    Runs the daily selection + content generation once.
    If send_email/create_calendar_event is True, you must have Google OAuth configured.
    """
    adventures = seed_adventures()
    weather = fetch_weather_for_day(criteria.date, timezone=cfg.timezone)
    adventure, _candidates = pick_daily_adventure(adventures, criteria, weather)

    md = generate_daily_markdown(cfg, adventure, criteria, weather)
    html = render_daily_email_html(adventure, criteria, criteria.date, md, weather)

    subject = f"Mikroabenteuer: {adventure.title} ({criteria.date.isoformat()})"

    # ICS: prefer a time slot if user provided start_time, else all-day
    ics = build_ics_event(
        day=criteria.date,
        summary=f"Mikroabenteuer: {adventure.title}",
        description=md,
        location=adventure.area,
        tzid=cfg.timezone,
        start_time_local=criteria.start_time,
        duration_minutes=adventure.duration_minutes,
    )

    if send_email:
        from .google_auth import get_credentials
        from .gmail_api import send_gmail_message

        scopes = ["https://www.googleapis.com/auth/gmail.send"]
        creds = get_credentials(
            cfg.google_client_secrets_file, cfg.google_token_file, scopes
        )

        send_gmail_message(
            creds,
            user_id="me",
            sender=cfg.gmail_from_email,
            to=cfg.gmail_to_email,
            subject=subject,
            html_body=html,
            ics_bytes=ics,
            ics_filename="mikroabenteuer.ics",
        )

    if create_calendar_event:
        # Optional: write to your shared calendar (separate from ICS)
        # Only possible if you have Calendar scopes & calendar_id configured.
        if criteria.start_time is not None:
            from .google_auth import get_credentials
            from .gcal_api import insert_calendar_event

            scopes = ["https://www.googleapis.com/auth/calendar.events"]
            creds = get_credentials(
                cfg.google_client_secrets_file, cfg.google_token_file, scopes
            )

            start_dt = datetime.combine(criteria.date, criteria.start_time)
            insert_calendar_event(
                creds,
                calendar_id=cfg.calendar_id,
                summary=f"Mikroabenteuer: {adventure.title}",
                description=md,
                location=adventure.area,
                start_dt=start_dt,
                duration_minutes=adventure.duration_minutes,
                timezone=cfg.timezone,
            )

    return DailyJobResult(
        subject=subject, to_email=cfg.gmail_to_email, adventure_slug=adventure.slug
    )


def start_scheduler_0820(
    cfg: AppConfig,
    criteria: ActivitySearchCriteria,
    *,
    send_email: bool = True,
    create_calendar_event: bool = False,
) -> None:
    """
    APScheduler daily job at 08:20 (Europe/Berlin).
    Run this in a separate process/container (NOT inside Streamlit).
    """
    from apscheduler.schedulers.blocking import BlockingScheduler  # type: ignore
    from pytz import timezone as pytz_timezone  # type: ignore

    tz = pytz_timezone(cfg.timezone)
    sched = BlockingScheduler(timezone=tz)

    def _job():
        run_daily_job_once(
            cfg,
            criteria,
            send_email=send_email,
            create_calendar_event=create_calendar_event,
        )

    sched.add_job(_job, "cron", hour=8, minute=20)
    sched.start()
