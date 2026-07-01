"""calkit — framework-agnostic iCalendar (.ics) generation.

Pure data in, RFC 5545 bytes out. No web/bot framework dependencies.

Public API:
    build_event(...)        -> bytes   # one VEVENT in a VCALENDAR
    build_calendar(events)  -> bytes   # many VEVENTs in a VCALENDAR
    build_todo(...)         -> bytes   # one VTODO (task) in a VCALENDAR
    google_template_url(...) -> str    # Google Calendar "add event" link

Apple Reminders via Shortcuts (pure strings/bytes, no network):
    shortcuts_reminder_url(...)     -> str        # shortcuts:// launch URL
    detect_apple(user_agent)        -> AppleDevice
    reminder_entry_mode(ua)         -> str        # "apple" | "unknown"
    reminder_landing_html(...)      -> str        # per-task landing page
    build_reminder_shortcut(...)    -> bytes      # unsigned .shortcut plist
    write_reminder_shortcut(...)    -> None       # write that plist to a file
    reminder_setup_instructions(...) -> list[str] # first-run steps
    reminder_setup_html(...)        -> str        # first-run setup page

Convenience dataclasses:
    Event, Alarm, AppleDevice
"""

from __future__ import annotations

from .core import (
    Alarm,
    Event,
    build_calendar,
    build_event,
    build_todo,
    google_template_url,
)
from .reminders import (
    AppleDevice,
    build_reminder_shortcut,
    detect_apple,
    reminder_entry_mode,
    reminder_landing_html,
    reminder_setup_html,
    reminder_setup_instructions,
    shortcuts_reminder_url,
    write_reminder_shortcut,
)

__all__ = [
    "Alarm",
    "AppleDevice",
    "Event",
    "build_calendar",
    "build_event",
    "build_todo",
    "build_reminder_shortcut",
    "detect_apple",
    "google_template_url",
    "reminder_entry_mode",
    "reminder_landing_html",
    "reminder_setup_html",
    "reminder_setup_instructions",
    "shortcuts_reminder_url",
    "write_reminder_shortcut",
]

__version__ = "0.4.0"
