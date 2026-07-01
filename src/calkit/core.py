"""Core iCalendar generation logic.

Framework-agnostic: takes plain Python data, returns RFC 5545 ``.ics`` bytes.
Built on top of the ``icalendar`` library, which handles the low-level
serialization and folding.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Iterable, Optional, Sequence, Union
from urllib.parse import urlencode
from uuid import uuid4
from zoneinfo import ZoneInfo

from icalendar import Alarm as _ICalAlarm
from icalendar import Calendar as _ICalCalendar
from icalendar import Event as _ICalEvent

__all__ = [
    "Alarm",
    "Event",
    "build_calendar",
    "build_event",
    "google_template_url",
]

PRODID = "-//calkit//calkit 0.1.0//EN"

# A "when" is either a timezone-aware/naive datetime (timed event) or a
# plain date (all-day event).
When = Union[_dt.datetime, _dt.date]


@dataclass(frozen=True)
class Alarm:
    """A single reminder relative to the event start.

    Attributes:
        trigger: Offset relative to the event start. Negative means *before*
            the start, e.g. ``-timedelta(hours=1)`` fires one hour before.
        description: Text shown by the calendar client for a DISPLAY alarm.
    """

    trigger: _dt.timedelta
    description: str = "Reminder"


@dataclass
class Event:
    """Convenience container for a single calendar event.

    Mirrors the keyword arguments of :func:`build_event`. Useful when passing
    a list of events to :func:`build_calendar`.
    """

    summary: str
    start: When
    end: Optional[When] = None
    all_day: bool = False
    tz: str = "UTC"
    location: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    alarms: Sequence[Union[Alarm, _dt.timedelta]] = field(default_factory=tuple)
    uid: Optional[str] = None
    organizer: Optional[str] = None


def _coerce_alarm(a: Union[Alarm, _dt.timedelta]) -> Alarm:
    if isinstance(a, Alarm):
        return a
    if isinstance(a, _dt.timedelta):
        return Alarm(trigger=a)
    raise TypeError(
        f"alarm must be an Alarm or datetime.timedelta, got {type(a).__name__}"
    )


def _apply_tz(value: When, tz: str, *, all_day: bool) -> When:
    """Attach timezone info to a datetime; pass dates through untouched."""
    if all_day:
        # All-day events use a plain date. If a datetime was passed, take
        # its date component so icalendar emits VALUE=DATE.
        if isinstance(value, _dt.datetime):
            return value.date()
        return value

    if not isinstance(value, _dt.datetime):
        # A bare date for a timed event: treat as midnight in the zone.
        value = _dt.datetime(value.year, value.month, value.day)

    zone = ZoneInfo(tz)
    if value.tzinfo is None:
        return value.replace(tzinfo=zone)
    return value


def _build_vevent(ev: Event) -> _ICalEvent:
    alarms = [_coerce_alarm(a) for a in ev.alarms]

    vevent = _ICalEvent()
    vevent.add("summary", ev.summary)

    dtstart = _apply_tz(ev.start, ev.tz, all_day=ev.all_day)
    vevent.add("dtstart", dtstart)

    if ev.end is not None:
        dtend = _apply_tz(ev.end, ev.tz, all_day=ev.all_day)
        vevent.add("dtend", dtend)
    elif ev.all_day:
        # RFC 5545: all-day DTEND is exclusive; default to the day after start.
        start_date = dtstart if isinstance(dtstart, _dt.date) else dtstart.date()
        vevent.add("dtend", start_date + _dt.timedelta(days=1))

    # Description: base text plus the URL appended, because some clients only
    # surface links found inside the DESCRIPTION body.
    description_parts = []
    if ev.description:
        description_parts.append(ev.description)
    if ev.url:
        description_parts.append(ev.url)
    if description_parts:
        vevent.add("description", "\n\n".join(description_parts))

    if ev.location:
        vevent.add("location", ev.location)

    if ev.url:
        vevent.add("url", ev.url)

    if ev.organizer:
        vevent.add("organizer", ev.organizer)

    uid = ev.uid or f"{uuid4()}@calkit"
    vevent.add("uid", uid)
    vevent.add("dtstamp", _dt.datetime.now(tz=_dt.timezone.utc))

    for alarm in alarms:
        valarm = _ICalAlarm()
        valarm.add("action", "DISPLAY")
        valarm.add("description", alarm.description)
        valarm.add("trigger", alarm.trigger)
        vevent.add_component(valarm)

    return vevent


def _finalize(cal: _ICalCalendar) -> bytes:
    # Embed VTIMEZONE components for any zones referenced by TZID, so the
    # file is self-contained and portable. Available in modern icalendar.
    add_missing = getattr(cal, "add_missing_timezones", None)
    if callable(add_missing):
        try:
            add_missing()
        except Exception:
            # Non-fatal: the file is still valid with TZID references.
            pass
    return cal.to_ical()


def _new_calendar() -> _ICalCalendar:
    cal = _ICalCalendar()
    cal.add("prodid", PRODID)
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    return cal


def build_event(
    *,
    summary: str,
    start: When,
    end: Optional[When] = None,
    all_day: bool = False,
    tz: str = "UTC",
    location: Optional[str] = None,
    url: Optional[str] = None,
    description: Optional[str] = None,
    alarms: Sequence[Union[Alarm, _dt.timedelta]] = (),
    uid: Optional[str] = None,
    organizer: Optional[str] = None,
) -> bytes:
    """Build a VCALENDAR containing a single VEVENT and return ``.ics`` bytes.

    Args:
        summary: Event title.
        start: Start datetime (or date when ``all_day``).
        end: Optional end datetime (or date when ``all_day``).
        all_day: If True, emit an all-day event using VALUE=DATE.
        tz: IANA/zoneinfo timezone name applied to naive datetimes.
        location: Optional location text.
        url: Optional link, written to the URL property *and* appended to the
            DESCRIPTION (some clients only render links from the description).
        description: Optional description body.
        alarms: Reminders as :class:`Alarm` objects or bare ``timedelta``
            offsets relative to the start (negative = before). Each becomes a
            VALARM with ACTION=DISPLAY.
        uid: Optional UID; generated if omitted.
        organizer: Optional organizer (e.g. ``"mailto:a@b.com"``).

    Returns:
        RFC 5545 ``.ics`` content as bytes.
    """
    ev = Event(
        summary=summary,
        start=start,
        end=end,
        all_day=all_day,
        tz=tz,
        location=location,
        url=url,
        description=description,
        alarms=tuple(alarms),
        uid=uid,
        organizer=organizer,
    )
    cal = _new_calendar()
    cal.add_component(_build_vevent(ev))
    return _finalize(cal)


def build_calendar(events: Iterable[Event]) -> bytes:
    """Build a VCALENDAR containing multiple VEVENTs.

    Args:
        events: Iterable of :class:`Event` instances.

    Returns:
        RFC 5545 ``.ics`` content as bytes.
    """
    cal = _new_calendar()
    for ev in events:
        cal.add_component(_build_vevent(ev))
    return _finalize(cal)


def _fmt_google_dt(value: When) -> str:
    """Format a datetime as UTC ``YYYYMMDDTHHMMSSZ`` for Google Calendar."""
    if isinstance(value, _dt.datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=_dt.timezone.utc)
        value = value.astimezone(_dt.timezone.utc)
        return value.strftime("%Y%m%dT%H%M%SZ")
    # Bare date -> all-day Google format YYYYMMDD.
    return value.strftime("%Y%m%d")


def google_template_url(
    *,
    summary: str,
    start: _dt.datetime,
    end: _dt.datetime,
    details: Optional[str] = None,
    location: Optional[str] = None,
) -> str:
    """Build a Google Calendar "add event" template URL.

    Google ignores VALARM from imported ``.ics`` files (it uses the account's
    default reminders), so offering this link alongside the ``.ics`` gives
    Google users a reliable path. Times are rendered in UTC.

    Args:
        summary: Event title (``text`` param).
        start: Start datetime.
        end: End datetime.
        details: Optional description (``details`` param).
        location: Optional location.

    Returns:
        A ``https://calendar.google.com/calendar/render?...`` URL.
    """
    dates = f"{_fmt_google_dt(start)}/{_fmt_google_dt(end)}"
    params = {
        "action": "TEMPLATE",
        "text": summary,
        "dates": dates,
    }
    if details is not None:
        params["details"] = details
    if location is not None:
        params["location"] = location

    query = urlencode(params)
    return f"https://calendar.google.com/calendar/render?{query}"
