# calkit

Framework-agnostic **iCalendar (`.ics`) generation** for Python.

Data in, RFC 5545 bytes out. No dependency on aiogram, FastAPI, Telegram, or any
web/bot framework — just pure functions that take event data and return `.ics`
bytes. Reuse the same core from Telegram bots and web backends alike.

Built on the reliable [`icalendar`](https://pypi.org/project/icalendar/) library
(BSD) for correct RFC 5545 serialization.

- Python 3.10+
- Typed (`py.typed` shipped)
- MIT licensed

> **PyPI naming note:** the distribution name in `pyproject.toml` is `calkit`.
> Before publishing to PyPI, verify the name is not already taken — if it is,
> rename the *distribution* and keep the *import* name `calkit`.

## Installation

```bash
pip install calkit          # once published
# or, from a local checkout:
pip install -e ".[dev]"
```

## Public API

```python
build_event(
    *, summary, start, end=None, all_day=False, tz="UTC",
    location=None, url=None, description=None,
    alarms=(), uid=None, organizer=None,
) -> bytes                       # one VEVENT inside a VCALENDAR

build_calendar(events) -> bytes  # many Event objects -> one VCALENDAR

google_template_url(
    *, summary, start, end, details=None, location=None,
) -> str                         # Google Calendar "add event" link
```

Convenience dataclasses `Event` and `Alarm` are also exported.

## Quick example

```python
import datetime as dt
from calkit import build_event, Alarm

ics = build_event(
    summary="Dentist appointment",
    start=dt.datetime(2026, 7, 1, 15, 0),
    end=dt.datetime(2026, 7, 1, 15, 45),
    tz="Europe/Berlin",
    location="Main St 5",
    url="https://example.com/booking/42",
    description="Bring the insurance card.",
    alarms=[
        -dt.timedelta(hours=1),                       # 1 hour before
        Alarm(-dt.timedelta(days=1), "Tomorrow!"),    # 1 day before, custom text
    ],
)

with open("event.ics", "wb") as f:
    f.write(ics)
```

All-day event:

```python
import datetime as dt
from calkit import build_event

ics = build_event(summary="Public holiday", start=dt.date(2026, 7, 4), all_day=True)
```

Multiple events in one calendar:

```python
import datetime as dt
from calkit import build_calendar, Event

ics = build_calendar([
    Event(summary="Kickoff", start=dt.datetime(2026, 7, 1, 9, 0), tz="UTC"),
    Event(summary="Review",  start=dt.datetime(2026, 7, 8, 9, 0), tz="UTC"),
])
```

## Delivery scenarios

The library only produces bytes/strings — *how you deliver them* is up to the
caller. Two common patterns (illustrative; not part of the library):

### 1. Telegram bot — send the `.ics` as a document

```python
import datetime as dt
from calkit import build_event
# aiogram v3 example
from aiogram.types import BufferedInputFile

ics = build_event(
    summary="Consultation",
    start=dt.datetime(2026, 7, 1, 15, 0),
    tz="Europe/Berlin",
)
await message.answer_document(
    BufferedInputFile(ics, filename="event.ics"),
    caption="Add this to your calendar",
)
```

### 2. Web / FastAPI — return a downloadable file + a Google button

```python
import datetime as dt
from fastapi import FastAPI
from fastapi.responses import Response
from calkit import build_event, google_template_url

app = FastAPI()

@app.get("/event.ics")
def event_ics():
    ics = build_event(
        summary="Consultation",
        start=dt.datetime(2026, 7, 1, 15, 0),
        end=dt.datetime(2026, 7, 1, 16, 0),
        tz="Europe/Berlin",
    )
    return Response(
        content=ics,
        media_type="text/calendar",
        headers={"Content-Disposition": 'attachment; filename="event.ics"'},
    )

# Render this URL as an "Add to Google Calendar" button next to the download:
gcal = google_template_url(
    summary="Consultation",
    start=dt.datetime(2026, 7, 1, 15, 0),
    end=dt.datetime(2026, 7, 1, 16, 0),
    details="See you there.",
    location="Main St 5",
)
```

## Cross-platform notes

Calendar clients differ in how they treat imported `.ics` files:

- **Reminders / VALARM.** Apple Calendar and Microsoft Outlook honor the
  `VALARM` reminders embedded in an imported `.ics`. **Google Calendar ignores
  them** — on import it discards file alarms and applies the *account's default*
  notifications instead. If reminders matter for Google users, offer a
  `google_template_url(...)` link alongside the `.ics` download: the template URL
  lets Google create the event natively (where the user's defaults apply, and the
  event is editable before saving).

- **Links.** Some clients only surface a link if it appears inside the event
  body. `calkit` therefore writes the URL to **both** the `URL` property **and**
  the end of `DESCRIPTION`, maximizing the chance the link is clickable.

- **Timezones.** `calkit` attaches the given `tz` (zoneinfo name) to naive
  datetimes and embeds the matching `VTIMEZONE` component, so the file is
  self-contained and portable.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT — see [LICENSE](LICENSE).
