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

# --- Apple Reminders via Shortcuts (pure strings/bytes, no network) ---

shortcuts_reminder_url(
    *, name, title, due=None, notes=None, url=None,
    tz="UTC", shortcut_input_extra=None,
) -> str                         # shortcuts://run-shortcut launch URL

detect_apple(user_agent) -> AppleDevice         # UA -> platform guess
reminder_entry_mode(user_agent) -> str          # "apple" | "unknown"
reminder_landing_html(
    *, shortcut_url, mode, lang="ru", labels=None,
) -> str                         # per-task self-contained landing page

# First-run setup (prepare the Shortcut once)
build_reminder_shortcut(*, name="Add Reminder") -> bytes   # unsigned .shortcut plist
write_reminder_shortcut(path, *, name="Add Reminder") -> None
reminder_setup_instructions(
    *, lang="ru", source="untrusted",
) -> list[str]                   # ordered first-run steps ("untrusted"|"icloud")
reminder_setup_html(
    *, install_url, source="icloud", lang="ru", labels=None, mode=None,
) -> str                         # self-contained first-run setup page
```

Convenience dataclasses `Event`, `Alarm`, and `AppleDevice` are also exported.

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

## Apple Reminders (Shortcuts)

Apple has no public URL scheme to create a **Reminders** task directly, but the
**Shortcuts** app does: a shortcut can receive a dictionary as *input* and add a
Reminder from it. `calkit` supplies the string plumbing for that flow (pure
functions — no network, no auth).

### Mechanics

1. **One-time setup (first run, per user).** The user installs one Shortcut
   that reads its dictionary *input* and creates a Reminder from a **fixed set
   of keys**. There are two install sources — see
   [First-run setup](#first-run-setup-preparing-the-shortcut) below. `calkit`
   can generate the setup material for either.
2. **Per-task launch.** For each task the project builds a
   `shortcuts://run-shortcut?name=<Shortcut name>&input=<JSON>` URL with
   `shortcuts_reminder_url(...)` and opens it on the Apple device. The Shortcut
   receives the JSON and creates the Reminder.

### Fixed payload keys (build your Shortcut against these)

The JSON passed as `input` always carries these keys, so your Shortcut has a
stable contract:

| key     | type        | meaning                                   |
| ------- | ----------- | ----------------------------------------- |
| `title` | `str`       | reminder title                            |
| `due`   | `str\|null` | ISO-8601 due date/time (offset if aware)  |
| `notes` | `str\|null` | free-text notes                           |
| `url`   | `str\|null` | associated link                           |

Extra fields can be merged in via `shortcut_input_extra` (e.g. a target list
name or priority) without breaking the fixed keys.

```python
import datetime as dt
from calkit import shortcuts_reminder_url

link = shortcuts_reminder_url(
    name="Add Reminder",                       # the installed Shortcut's name
    title="Call the dentist",
    due=dt.datetime(2026, 7, 1, 15, 0),        # naive -> localized to tz below
    notes="Bring the insurance card.",
    url="https://example.com/booking/42",
    tz="Europe/Berlin",
    shortcut_input_extra={"list": "Personal"}, # optional extra fields
)
# shortcuts://run-shortcut?name=Add%20Reminder&input=%7B%22title%22%3A...%7D
```

`name` and the JSON `input` are fully URL-escaped; the JSON is compact and
`ensure_ascii=False`, so non-ASCII text stays readable before percent-encoding.

### First-run setup (preparing the Shortcut)

Per-task launch (above) only works once the Shortcut is installed. `calkit`
carries the **first-run onboarding** as a library concern, so a project does
not assemble the Shortcut or the setup page by hand.

**Honest Apple limit — read this first.** An Apple-**signed** iCloud share link
(`https://www.icloud.com/shortcuts/...`) **cannot be generated from code** — the
signature is minted on Apple's side. So there are two install sources:

| source        | how it's obtained                                             | user friction on device                                                             | recommendation           |
| ------------- | ------------------------------------------------------------- | ----------------------------------------------------------------------------------- | ------------------------ |
| `"untrusted"` | **`build_reminder_shortcut()`** generates an unsigned `.shortcut` | must enable **"Allow Untrusted Shortcuts"** in Settings + run it **once manually** to grant Reminders access | self-contained fallback  |
| `"icloud"`    | a human publishes the Shortcut once and pastes its iCloud link | none — tap to add                                                                    | **recommended for prod** |

The first-run onboarding works with either source; you pick which via the
`source` argument and the `install_url` you pass.

> ⚠️ **The generated `.shortcut` is not verified on a physical Apple device.**
> `build_reminder_shortcut()` emits a valid binary property list using Apple's
> documented action identifiers (`is.workflow.actions.detect.dictionary`,
> `is.workflow.actions.getvalueforkey`, `is.workflow.actions.addnewreminder`)
> and the standard magic-variable serialization, but the exact runtime wiring
> (due-date alarm, notes concatenation) has **not** been round-tripped on a real
> device — treat the first on-device import as a one-time validation step.

**(A) built-in unsigned `.shortcut`:**

```python
from calkit import build_reminder_shortcut, write_reminder_shortcut

data = build_reminder_shortcut(name="Add Reminder")   # -> bytes (binary plist)
write_reminder_shortcut("add-reminder.shortcut", name="Add Reminder")
# Serve `data` from an endpoint, or attach the file. Then point the setup
# page's install button at that download URL with source="untrusted".
```

**Setup page and steps** (works for either source):

```python
from calkit import (
    reminder_setup_instructions,
    reminder_setup_html,
    reminder_entry_mode,
)

# Plain ordered steps (render however you like):
steps = reminder_setup_instructions(lang="ru", source="untrusted")

# Or a full self-contained page: numbered steps + an "Install" button on
# install_url + a "I've installed it -> continue" hook (id="reminder-continue",
# which your app wires to its next step). Pass mode="unknown" to warn a
# non-Apple visitor; an inline script re-checks the client (incl. iPadOS
# masquerade via maxTouchPoints).
mode = reminder_entry_mode(request.headers.get("User-Agent"))
html = reminder_setup_html(
    install_url="https://www.icloud.com/shortcuts/abc123",  # signed iCloud link
    source="icloud",
    lang="ru",
    mode=mode,
)
```

**Whether the Shortcut is already installed is state the project owns.** The
library does not track it. Your flow is: on a user's first reminder, show
`reminder_setup_html(...)`; once they confirm install (your "continue" hook),
remember that and from then on go straight to the per-task
`reminder_landing_html(...)` + `shortcuts_reminder_url(...)` path.

Full first-run → per-task flow:

1. **First run:** user has no Shortcut yet → render `reminder_setup_html(...)`
   with your chosen `source`/`install_url`; user installs it and taps continue;
   your project records "installed".
2. **Per task, thereafter:** build the launch URL with
   `shortcuts_reminder_url(...)` and hand it to the user via
   `reminder_landing_html(...)` (or your own UI).

### Telegram nuance

Telegram **inline buttons reject custom schemes** like `shortcuts://` — they
only accept `http(s)://`. So don't put the `shortcuts://` URL on an inline
button directly. Instead, host a small **https landing page** and link the
button there; the landing page carries the `shortcuts://` link as a normal
anchor the user taps. `reminder_landing_html(...)` renders exactly such a page.

### Auto-detection and two UX states

`detect_apple(user_agent)` classifies the visitor's `User-Agent` into an
`AppleDevice(is_apple, kind)` where `kind` is one of
`iphone`/`ipad`/`ipod`/`mac`/`unknown`. `reminder_entry_mode(user_agent)`
collapses that to `"apple"` or `"unknown"`.

> Limitation: iPadOS Safari can masquerade as `Macintosh`, so a modern iPad may
> report `kind="mac"` — still `is_apple=True`, which is all this flow needs.

`reminder_landing_html(...)` renders a self-contained, dependency-free page with
two states:

- **`mode="apple"`** — Apple detected: shows the action as an explicit tool, a
  prominent "📋 Добавить в Напоминания" button linking to the `shortcuts://` URL.
- **`mode="unknown"`** — not detected: shows the **same button as an option**
  plus a warning that it only works on an Apple device, and the user may
  continue if they are on one.

An inline `<script>` re-checks `navigator` on the client (more accurate than the
server's UA guess, and handles the iPadOS masquerade via `maxTouchPoints`); if
it finds Apple, it flips an `unknown` page into the explicit-tool state. Default
texts ship for `lang="ru"` and `lang="en"`; `labels` overrides any string.

```python
from calkit import reminder_entry_mode, shortcuts_reminder_url, reminder_landing_html

mode = reminder_entry_mode(request.headers.get("User-Agent"))
link = shortcuts_reminder_url(name="Add Reminder", title="Call the dentist")
html = reminder_landing_html(shortcut_url=link, mode=mode, lang="ru")
# return `html` as text/html from your web handler
```

`reminder_landing_html` is an **optional convenience helper** — a project can
render its own UI using `reminder_entry_mode` + `shortcuts_reminder_url`.

> **Scope:** this path is Apple-only. For non-Apple users, fall back to a
> calendar reminder (`build_event(...)` with a `VALARM`, or
> `google_template_url(...)`) or another task-provider integration.

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
