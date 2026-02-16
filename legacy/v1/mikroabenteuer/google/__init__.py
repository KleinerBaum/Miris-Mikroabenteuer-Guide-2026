"""Google API integrations for calendar and Gmail workflows."""

from .auth import get_credentials
from .calendar_service import create_event, list_events
from .gmail_service import send_daily_mail, send_html_email

__all__ = [
    "create_event",
    "get_credentials",
    "list_events",
    "send_daily_mail",
    "send_html_email",
]
