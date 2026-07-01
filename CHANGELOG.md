# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.1] - 2026-07-01

### Fixed
- `build_event` / `build_todo`: accept **ISO-8601 strings** for `start` / `end`
  / `due` (previously any string raised `AttributeError` in `_apply_tz`). A
  trailing `Z` (UTC) is handled for Python 3.10 compatibility. `When` now
  includes `str`.

## [0.4.0] - 2026-07-01

### Added
- `build_todo(*, summary, due=None, start=None, all_day=False, tz="UTC",
  location=None, url=None, description=None, alarms=(), priority=None,
  status=None, uid=None) -> bytes` — build a VCALENDAR with a single **VTODO**
  (task), returned as `.ics` bytes. Symmetric to `build_event`: same timezone
  handling (zoneinfo + embedded `VTIMEZONE`), URL written to both the `URL`
  property and the end of `DESCRIPTION`, and `VALARM` reminders from
  `timedelta`/`Alarm` triggers. Task-specific properties: `DUE`, optional
  `DTSTART`, `PRIORITY` (integer 0–9, out-of-range → `ValueError`), and `STATUS`
  (`NEEDS-ACTION`/`IN-PROCESS`/`COMPLETED`/`CANCELLED`, anything else →
  `ValueError`). All-day tasks emit `VALUE=DATE`. UID generated if omitted, plus
  `DTSTAMP`. Exported from the package (`build_todo`).
- **CI (GitHub Actions):** `.github/workflows/ci.yml` runs the test suite on
  `push`/`pull_request` to `main` across Python 3.10, 3.11, 3.12, and 3.13.
  CI badge added to the README.

## [0.3.0] - 2026-07-01

### Added
- First-run Shortcut onboarding, moved into the library so projects no longer
  assemble the Shortcut or the setup page by hand:
  - `build_reminder_shortcut(*, name="Add Reminder") -> bytes` — generate an
    **unsigned** `.shortcut` file (binary property list via `plistlib`,
    `FMT_BINARY`) whose workflow parses the JSON input into a dictionary
    (`is.workflow.actions.detect.dictionary`), reads the fixed keys
    `title`/`due`/`notes`/`url` (`is.workflow.actions.getvalueforkey`), and adds
    a Reminder (`is.workflow.actions.addnewreminder`) with
    `notes = notes + "\n" + url` and a due alarm from `due`. Payload keys match
    `shortcuts_reminder_url`.
  - `write_reminder_shortcut(path, *, name="Add Reminder") -> None` — write that
    plist to a file.
  - `reminder_setup_instructions(*, lang="ru", source="untrusted") -> list[str]`
    — ordered first-run steps for `source` ∈ {`"untrusted"`, `"icloud"`}, RU/EN.
  - `reminder_setup_html(*, install_url, source="icloud", lang="ru",
    labels=None, mode=None) -> str` — self-contained setup page: numbered steps
    + "Install the Shortcut" button on `install_url` + an "I've installed it →
    continue" hook; reuses the Apple detection/warning + client re-check
    (`maxTouchPoints`) from `reminder_landing_html`; escaped interpolation;
    `labels` overrides.

### Notes
- **Honest Apple limit:** an Apple-*signed* iCloud share link cannot be minted
  from code (signing is on Apple's side). Hence two install sources — an unsigned
  built-in `.shortcut` (requires "Allow Untrusted Shortcuts" + a one-time manual
  run) and a signed iCloud link published once by a human (recommended for prod).
- The generated `.shortcut` uses documented action identifiers and standard
  magic-variable serialization but has **not** been round-trip verified on a
  physical Apple device; treat the first on-device import as a validation step.

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
