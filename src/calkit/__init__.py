"""calkit — framework-agnostic iCalendar (.ics) generation.

Pure data in, RFC 5545 bytes out. No web/bot framework dependencies.

Public API:
    build_event(...)        -> bytes   # one VEVENT in a VCALENDAR
    build_calendar(events)  -> bytes   # many VEVENTs in a VCALENDAR
    google_template_url(...) -> str    # Google Calendar "add event" link

Convenience dataclasses:
    Event, Alarm
"""

from __future__ import annotations

from .core import (
    Alarm,
    Event,
    build_calendar,
    build_event,
    google_template_url,
)

__all__ = [
    "Alarm",
    "Event",
    "build_calendar",
    "build_event",
    "google_template_url",
]

__version__ = "0.1.0"
