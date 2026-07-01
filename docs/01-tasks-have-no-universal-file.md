# Tasks have no universal file

*How calkit models reminders once you accept there is no `.ics` for tasks.*

## TL;DR

Calendars have a portable, universal file: hand someone an `.ics` and it opens in
Apple Calendar, Google Calendar, Outlook — the event lands. **Tasks have no such
file.** There is no single artifact you can generate that will create a to-do in
*whatever* task manager the user happens to run. Chasing "one file for all tasks"
is a dead end. `calkit` instead uses a **layered design**: `.ics` `VTODO` for the
clients that read it, provider APIs for the ones that don't, and — for Apple
Reminders, which has neither a public creation URL nor an importable task file —
a **Shortcuts**-driven flow. The library stays a pure builder of strings and
bytes plus first-run onboarding; anything needing auth or secrets stays in the
calling project.

## Context / research

### Why calendars are easy

The calendar world standardized on **iCalendar (RFC 5545)**. A `VEVENT` inside a
`VCALENDAR` is understood everywhere, and every major client imports a `.ics`
file from a download, an email attachment, or a share sheet. One file, universal
reach. That is exactly what `calkit`'s `build_event` / `build_calendar` exploit.

### Why tasks are not

RFC 5545 *does* define a task component — **`VTODO`** — with `DUE`, `PRIORITY`,
`STATUS`, `PERCENT-COMPLETE`, and `VALARM`. On paper, tasks have a standard. In
practice the **import path is missing on the platforms that matter most**:

| Target | Reads a `VTODO`/`.ics` task on import? | Has a URL scheme to create a task? | Practical creation mechanic |
| ------ | ------------------------------------- | ---------------------------------- | --------------------------- |
| **Apple Reminders** | No (Reminders does not import `.ics` tasks) | No public "create reminder" URL | **Shortcuts** app: a shortcut takes a dictionary input and adds a Reminder |
| **Google Tasks** | No | No documented deep link | Google Tasks **REST API** (OAuth) |
| **Todoist** | No | `todoist://` is app-nav, not reliable task-create | **REST API** (token), or `mailto` add-by-email |
| **Microsoft To Do** | No | No | **Microsoft Graph API** (OAuth) |
| **CalDAV task servers** (Nextcloud Tasks, Tasks.org, etc.) | **Yes** — `VTODO` over CalDAV is the native model | n/a (protocol, not a link) | `PUT` a `VTODO` to a CalDAV collection |

So the honest picture is a **matrix, not a file**: only CalDAV-family clients
consume a `VTODO` directly; the big consumer platforms each require their own
mechanic — an API with auth, or, in Apple's case, a Shortcut.

**Prior art / license notes.** iCalendar serialization itself is a solved problem
handled by [`icalendar`](https://pypi.org/project/icalendar/) (BSD-2-Clause,
safe to depend on) — `calkit` builds on it rather than re-implementing folding
and `VTIMEZONE`. Provider client libraries (`google-api-python-client`,
`todoist-api-python`, `msal`/Graph SDKs) exist and are permissively licensed, but
each drags in auth, HTTP, and token storage — concerns that must live in the
*application*, not in a pure builder. That boundary is the core design lesson,
not a library to copy.

## Before / after

### Before — the naive idea: "one file for all tasks"

The tempting mental model, carried over from calendars:

> "Just generate a task file — a `.ics` with a `VTODO`, or *some* universal
> task file — and every task app will import it, like events."

This breaks the moment you test it on a real phone:

- Apple **Reminders** silently ignores the `VTODO` — the `.ics` opens in
  **Calendar** as an event, not as a reminder.
- Google **Tasks** offers no import at all.
- Todoist / MS To Do treat the file as unknown.
- Only niche CalDAV clients do the "right" thing — and reaching them still needs
  server URL + credentials, i.e. auth, not a file.

One artifact cannot span these because there is **no shared import contract for
tasks** the way there is for events.

### After — a layered design

Accept the matrix and split responsibilities into layers, each honest about what
it can do from pure code:

1. **`VTODO` in `.ics`** — for the CalDAV-family and any client that *does* read a
   task file. This is the "universal-ish file" layer, valid where a file works.
2. **Provider APIs** — Google Tasks, Todoist, Microsoft To Do. These need OAuth /
   tokens and live network calls. `calkit` deliberately **does not** own this
   layer: a pure, secret-free builder cannot hold credentials. The *application*
   wires the provider client; `calkit` supplies the data.
3. **Apple Shortcuts** — Apple Reminders has no importable task file and no public
   creation URL, but the **Shortcuts** app can: a shortcut reads a dictionary
   *input* and adds a Reminder. `calkit` supplies the entire string/bytes
   plumbing for this — the `shortcuts://run-shortcut` launch URL
   (`shortcuts_reminder_url`), a **fixed JSON payload contract**
   (`title`/`due`/`notes`/`url`), an unsigned `.shortcut` file builder
   (`build_reminder_shortcut`), Apple platform detection (`detect_apple`), and
   first-run onboarding pages (`reminder_setup_html`, `reminder_landing_html`).

The layers share one contract — the same fixed payload keys — so the mechanic can
change (unsigned file today, signed iCloud link tomorrow, a provider API later)
without the calling code changing shape.

## Pitfalls

- **`VTODO` validity ≠ reachability.** A perfectly valid `VTODO` still won't reach
  Apple Reminders or Google Tasks. Emit it for CalDAV, but don't promise it to
  everyone.
- **Apple has no "create reminder" URL scheme.** The Shortcuts detour is the
  supported path, not a workaround you can skip.
- **A signed iCloud Shortcut link cannot be minted from code.** Apple signs on its
  side. Hence two honest install sources: an unsigned `.shortcut` (needs "Allow
  Untrusted Shortcuts" + one manual run) as a self-contained fallback, and a
  human-published signed iCloud link (recommended for production).
- **iPadOS Safari masquerades as `Macintosh`.** Server-side UA detection may miss
  a modern iPad; a client-side re-check via `navigator.maxTouchPoints` closes the
  gap.
- **Telegram inline buttons reject custom schemes.** `shortcuts://` only works
  from an `http(s)` landing page's anchor, not from an inline button.
- **Provider APIs mean secrets.** The moment you touch Google/Todoist/MS To Do you
  own OAuth, token refresh, and storage — keep that out of the pure builder.

## Takeaway

`calkit`'s role is **clean builders + first-run onboarding**, not a universal task
file that doesn't exist. It generates the portable artifact where one exists
(`.ics`, `VTODO`, Google links), and supplies the exact offline plumbing for the
one platform that needs a detour (Apple Reminders via Shortcuts). Everything that
requires an account, a token, or a secret — the provider-API layer, hosting a
signed link — stays in the application, by design. The universal file for tasks
isn't missing from `calkit`; it's missing from the world, and the layered design
is what you build once you stop pretending otherwise.
