"""calkit — framework-agnostic iCalendar (.ics) generation.

Pure data in, RFC 5545 bytes out. No web/bot framework dependencies.

Public API:
    build_event(...)        -> bytes   # one VEVENT in a VCALENDAR
    build_calendar(events)  -> bytes   # many VEVENTs in a VCALENDAR
    google_template_url(...) -> str    # Google Calendar "add event" link

Apple Reminders via Shortcuts (pure strings, no network):
    shortcuts_reminder_url(...) -> str        # shortcuts:// launch URL
    detect_apple(user_agent)    -> AppleDevice
    reminder_entry_mode(ua)     -> str        # "apple" | "unknown"
    reminder_landing_html(...)  -> str        # optional landing page

Convenience dataclasses:
    Event, Alarm, AppleDevice
"""

from __future__ import annotations

from .core import (
    Alarm,
    Event,
    build_calendar,
    build_event,
    google_template_url,
)
from .reminders import (
    AppleDevice,
    detect_apple,
    reminder_entry_mode,
    reminder_landing_html,
    shortcuts_reminder_url,
)

__all__ = [
    "Alarm",
    "AppleDevice",
    "Event",
    "build_calendar",
    "build_event",
    "detect_apple",
    "google_template_url",
    "reminder_entry_mode",
    "reminder_landing_html",
    "shortcuts_reminder_url",
]

__version__ = "0.2.0"
