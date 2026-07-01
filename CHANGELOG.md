# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
