# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-07-01

### Added
- `shortcuts_reminder_url(...)` — build a `shortcuts://run-shortcut` launch URL
  that hands a compact JSON payload (fixed keys `title`/`due`/`notes`/`url`,
  plus optional `shortcut_input_extra`) to an Apple Shortcut, which creates a
  Reminder. Fully URL-escaped `name` and `input`; naive `due` datetimes are
  localized to `tz` and serialized as ISO-8601.
- `detect_apple(user_agent) -> AppleDevice` — classify a `User-Agent` into
  `iphone`/`ipad`/`ipod`/`mac`/`unknown` (specific tokens checked before
  iPhone/Mac to handle iPod/iPad UAs that embed "iPhone OS"/"Mac OS X").
- `reminder_entry_mode(user_agent) -> str` — `"apple"` or `"unknown"`.
- `reminder_landing_html(...)` — optional self-contained HTML landing page with
  two UX states (explicit tool vs. option + warning), RU/EN default labels,
  `labels` overrides, escaped interpolation, and an inline client-side Apple
  re-check (handles iPadOS masquerade via `maxTouchPoints`).
- `AppleDevice` dataclass exported.

## [0.1.0] - 2026-07-01

### Added
- `build_event(...)` — build a VCALENDAR with a single VEVENT, returned as
  `.ics` bytes. Supports timed and all-day events, timezones (zoneinfo),
  location, URL, description, organizer, custom/generated UID, DTSTAMP, and
  multiple DISPLAY alarms from `timedelta`/`Alarm` triggers.
- `build_calendar(events)` — build a VCALENDAR with multiple VEVENTs.
- `google_template_url(...)` — build a Google Calendar "add event" template URL.
- `Event` and `Alarm` convenience dataclasses.
- URL written to both the `URL` property and appended to `DESCRIPTION` for
  broader client compatibility.
- Embedded `VTIMEZONE` for self-contained, portable files.
- Typed package (`py.typed`).
