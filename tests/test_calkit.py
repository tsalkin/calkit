"""Tests for calkit: parse generated .ics back with icalendar and assert."""

from __future__ import annotations

import datetime as dt
from urllib.parse import parse_qs, urlparse

import pytest
from icalendar import Calendar

from calkit import Alarm, Event, build_calendar, build_event, google_template_url


def _parse(ics: bytes) -> Calendar:
    assert isinstance(ics, bytes)
    return Calendar.from_ical(ics)


def _events(cal: Calendar):
    return [c for c in cal.walk("VEVENT")]


def _alarms(vevent):
    return [c for c in vevent.walk("VALARM")]


def test_build_event_basic_roundtrip():
    ics = build_event(
        summary="Standup",
        start=dt.datetime(2026, 7, 1, 9, 0),
        end=dt.datetime(2026, 7, 1, 9, 30),
        tz="Europe/Berlin",
        location="Room 1",
    )
    cal = _parse(ics)
    assert cal.get("prodid")
    assert str(cal.get("version")) == "2.0"

    events = _events(cal)
    assert len(events) == 1
    ev = events[0]
    assert str(ev.get("summary")) == "Standup"
    assert str(ev.get("location")) == "Room 1"
    assert ev.get("uid") is not None
    assert ev.get("dtstamp") is not None
    assert ev.get("dtstart") is not None
    assert ev.get("dtend") is not None


def test_uid_generated_and_respected():
    ics_auto = build_event(summary="A", start=dt.datetime(2026, 7, 1, 9, 0))
    uid_auto = str(_events(_parse(ics_auto))[0].get("uid"))
    assert uid_auto  # non-empty

    ics_fixed = build_event(
        summary="A", start=dt.datetime(2026, 7, 1, 9, 0), uid="my-uid-123"
    )
    assert str(_events(_parse(ics_fixed))[0].get("uid")) == "my-uid-123"


def test_timezone_applied():
    ics = build_event(
        summary="TZ",
        start=dt.datetime(2026, 7, 1, 9, 0),
        tz="Europe/Berlin",
    )
    ev = _events(_parse(ics))[0]
    dtstart = ev.get("dtstart").dt
    assert isinstance(dtstart, dt.datetime)
    assert dtstart.tzinfo is not None
    # UTC offset for Berlin in July is +02:00 (CEST).
    assert dtstart.utcoffset() == dt.timedelta(hours=2)
    # VTIMEZONE embedded for portability.
    assert any(c.name == "VTIMEZONE" for c in _parse(ics).walk())


def test_all_day_uses_value_date():
    ics = build_event(
        summary="Holiday",
        start=dt.date(2026, 7, 4),
        all_day=True,
    )
    text = ics.decode("utf-8")
    assert "DTSTART;VALUE=DATE:20260704" in text
    ev = _events(_parse(ics))[0]
    dtstart = ev.get("dtstart").dt
    # A plain date, not a datetime.
    assert isinstance(dtstart, dt.date) and not isinstance(dtstart, dt.datetime)


def test_single_alarm_trigger_matches_timedelta():
    trigger = -dt.timedelta(hours=1)
    ics = build_event(
        summary="Meeting",
        start=dt.datetime(2026, 7, 1, 9, 0),
        alarms=[trigger],
    )
    ev = _events(_parse(ics))[0]
    alarms = _alarms(ev)
    assert len(alarms) == 1
    valarm = alarms[0]
    assert str(valarm.get("action")) == "DISPLAY"
    assert valarm.get("trigger").dt == trigger


def test_multiple_alarms():
    triggers = [-dt.timedelta(hours=1), -dt.timedelta(minutes=10), -dt.timedelta(days=1)]
    ics = build_event(
        summary="Big Event",
        start=dt.datetime(2026, 7, 1, 9, 0),
        alarms=[Alarm(trigger=t, description=f"in {t}") for t in triggers],
    )
    ev = _events(_parse(ics))[0]
    alarms = _alarms(ev)
    assert len(alarms) == 3
    got = {a.get("trigger").dt for a in alarms}
    assert got == set(triggers)


def test_bare_timedelta_alarm_accepted():
    ics = build_event(
        summary="X",
        start=dt.datetime(2026, 7, 1, 9, 0),
        alarms=(-dt.timedelta(minutes=15),),
    )
    ev = _events(_parse(ics))[0]
    assert _alarms(ev)[0].get("trigger").dt == -dt.timedelta(minutes=15)


def test_url_in_both_url_and_description():
    url = "https://example.com/event/42"
    ics = build_event(
        summary="Launch",
        start=dt.datetime(2026, 7, 1, 9, 0),
        url=url,
        description="Product launch.",
    )
    ev = _events(_parse(ics))[0]
    assert str(ev.get("url")) == url
    desc = str(ev.get("description"))
    assert url in desc
    assert "Product launch." in desc


def test_url_appended_even_without_description():
    url = "https://example.com/x"
    ics = build_event(summary="Y", start=dt.datetime(2026, 7, 1, 9, 0), url=url)
    ev = _events(_parse(ics))[0]
    assert str(ev.get("url")) == url
    assert url in str(ev.get("description"))


def test_organizer():
    ics = build_event(
        summary="O",
        start=dt.datetime(2026, 7, 1, 9, 0),
        organizer="mailto:host@example.com",
    )
    ev = _events(_parse(ics))[0]
    assert "host@example.com" in str(ev.get("organizer"))


def test_build_calendar_multiple_events():
    events = [
        Event(summary="One", start=dt.datetime(2026, 7, 1, 9, 0), tz="UTC"),
        Event(summary="Two", start=dt.datetime(2026, 7, 2, 10, 0), tz="UTC"),
        Event(summary="Three", start=dt.date(2026, 7, 3), all_day=True),
    ]
    ics = build_calendar(events)
    cal = _parse(ics)
    summaries = {str(e.get("summary")) for e in _events(cal)}
    assert summaries == {"One", "Two", "Three"}


def test_google_template_url_basic():
    url = google_template_url(
        summary="Team Sync",
        start=dt.datetime(2026, 7, 1, 9, 0, tzinfo=dt.timezone.utc),
        end=dt.datetime(2026, 7, 1, 10, 0, tzinfo=dt.timezone.utc),
        details="Weekly sync & planning",
        location="HQ, Floor 3",
    )
    assert url.startswith("https://calendar.google.com/calendar/render?")
    parsed = urlparse(url)
    q = parse_qs(parsed.query)
    assert q["action"] == ["TEMPLATE"]
    assert q["text"] == ["Team Sync"]
    assert q["dates"] == ["20260701T090000Z/20260701T100000Z"]
    assert q["details"] == ["Weekly sync & planning"]
    assert q["location"] == ["HQ, Floor 3"]


def test_google_template_url_escapes_special_chars():
    url = google_template_url(
        summary="A & B / C?",
        start=dt.datetime(2026, 7, 1, 9, 0),
        end=dt.datetime(2026, 7, 1, 10, 0),
    )
    # Raw special chars must be percent/plus-encoded, not literal in the query.
    query = urlparse(url).query
    assert "A & B / C?" not in query
    # But decode round-trips to the original.
    q = parse_qs(urlparse(url).query)
    assert q["text"] == ["A & B / C?"]


def test_google_template_url_naive_datetime_treated_as_utc():
    url = google_template_url(
        summary="X",
        start=dt.datetime(2026, 7, 1, 9, 0),
        end=dt.datetime(2026, 7, 1, 10, 0),
    )
    q = parse_qs(urlparse(url).query)
    assert q["dates"] == ["20260701T090000Z/20260701T100000Z"]


def test_invalid_alarm_type_raises():
    with pytest.raises(TypeError):
        build_event(
            summary="Bad",
            start=dt.datetime(2026, 7, 1, 9, 0),
            alarms=["not-an-alarm"],
        )
