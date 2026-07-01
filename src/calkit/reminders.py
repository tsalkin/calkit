"""Apple Reminders via Apple Shortcuts — pure string helpers.

Framework-agnostic and offline: task data in, strings out. No network, no
auth, no secrets. The functions here help a project drive Apple's Shortcuts
app to create a **Reminders** task, and detect whether the current visitor is
on an Apple platform (so the button can be surfaced appropriately).

Mechanics (out of scope for this library, but useful to understand the API):

1. **One-time setup.** The project ships a Shortcut (installed once via an
   iCloud share link) that reads its dictionary *input* and adds a Reminder.
2. **Per-task launch.** For each task the project builds a
   ``shortcuts://run-shortcut?name=...&input=<JSON>`` URL with
   :func:`shortcuts_reminder_url` and opens it on the Apple device; the
   Shortcut receives the JSON as input and creates the Reminder.

The JSON payload uses a **fixed set of keys** so the Shortcut can be built
against a stable contract:

    title  (str)        -- reminder title
    due    (str|None)   -- ISO-8601 due date/time (with offset if tz-aware)
    notes  (str|None)   -- free-text notes
    url    (str|None)   -- associated link

Extra keys may be merged in via ``shortcut_input_extra``.

Public API:
    shortcuts_reminder_url(...) -> str    # shortcuts:// launch URL
    detect_apple(user_agent)   -> AppleDevice
    reminder_entry_mode(ua)    -> str     # "apple" | "unknown"
    reminder_landing_html(...) -> str     # optional convenience landing page
"""

from __future__ import annotations

import datetime as _dt
import json as _json
from dataclasses import dataclass
from html import escape as _escape
from typing import Any, Mapping, Optional, Union
from urllib.parse import quote
from zoneinfo import ZoneInfo

__all__ = [
    "AppleDevice",
    "shortcuts_reminder_url",
    "detect_apple",
    "reminder_entry_mode",
    "reminder_landing_html",
]


# --------------------------------------------------------------------------- #
# 1. Shortcuts launch URL
# --------------------------------------------------------------------------- #

def _fmt_due(due: Union[_dt.datetime, _dt.date, str], tz: str) -> str:
    """Serialize a due value to an ISO-8601 string.

    A naive ``datetime`` is localized to ``tz`` first; an aware one is kept as
    is. A bare ``date`` and a pre-formatted ``str`` pass through (a ``str`` is
    trusted to already be ISO-8601).
    """
    if isinstance(due, str):
        return due
    if isinstance(due, _dt.datetime):
        if due.tzinfo is None:
            due = due.replace(tzinfo=ZoneInfo(tz))
        return due.isoformat()
    if isinstance(due, _dt.date):
        return due.isoformat()
    raise TypeError(
        f"due must be datetime, date or str, got {type(due).__name__}"
    )


def shortcuts_reminder_url(
    *,
    name: str,
    title: str,
    due: Optional[Union[_dt.datetime, _dt.date, str]] = None,
    notes: Optional[str] = None,
    url: Optional[str] = None,
    tz: str = "UTC",
    shortcut_input_extra: Optional[Mapping[str, Any]] = None,
) -> str:
    """Build a ``shortcuts://run-shortcut`` URL that adds an Apple Reminder.

    The URL launches the Shortcut named ``name`` and passes a compact JSON
    dictionary as its ``input``. The payload carries a **fixed set of keys**
    the receiving Shortcut is built against:

        title  (str)        -- from ``title``
        due    (str|None)   -- ISO-8601 from ``due`` (see below)
        notes  (str|None)   -- from ``notes``
        url    (str|None)   -- from ``url``

    Any keys in ``shortcut_input_extra`` are merged into the payload (they may
    override the fixed keys if they collide).

    Args:
        name: The exact Shortcut name as installed on the device.
        title: Reminder title.
        due: Optional due date/time. A naive ``datetime`` is localized to
            ``tz`` and serialized with its offset; an aware ``datetime`` keeps
            its own zone; a ``date`` becomes ``YYYY-MM-DD``; a ``str`` is
            passed through unchanged (assumed already ISO-8601).
        notes: Optional notes text.
        url: Optional associated link.
        tz: IANA/zoneinfo name used to localize a naive ``due`` datetime.
        shortcut_input_extra: Optional extra fields merged into the payload.

    Returns:
        A ``shortcuts://run-shortcut?name=<enc>&input=<enc JSON>`` string with
        both ``name`` and the JSON ``input`` fully URL-escaped. The JSON is
        compact (no spaces) and built with ``ensure_ascii=False`` so non-ASCII
        text stays readable before being percent-encoded.
    """
    payload: dict[str, Any] = {
        "title": title,
        "due": _fmt_due(due, tz) if due is not None else None,
        "notes": notes,
        "url": url,
    }
    if shortcut_input_extra:
        payload.update(shortcut_input_extra)

    input_json = _json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    # safe="" -> escape everything reserved (including / : ? & = and non-ASCII).
    enc_name = quote(name, safe="")
    enc_input = quote(input_json, safe="")
    return f"shortcuts://run-shortcut?name={enc_name}&input={enc_input}"


# --------------------------------------------------------------------------- #
# 2. Apple platform detection
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class AppleDevice:
    """Result of :func:`detect_apple`.

    Attributes:
        is_apple: True if the User-Agent looks like an Apple platform.
        kind: One of ``"iphone"``, ``"ipad"``, ``"ipod"``, ``"mac"``,
            ``"unknown"``.
    """

    is_apple: bool
    kind: str


def detect_apple(user_agent: Optional[str]) -> AppleDevice:
    """Detect whether a User-Agent string is an Apple platform.

    Matching (case-insensitive):
        * ``iPhone``            -> ``iphone``
        * ``iPad``              -> ``ipad``
        * ``iPod``              -> ``ipod``
        * ``Macintosh`` / ``Mac OS X`` (without iPhone/iPad) -> ``mac``
        * anything else / empty / ``None`` -> ``unknown`` (is_apple=False)

    Limitation: **iPadOS Safari can masquerade as ``Macintosh``** (desktop-class
    browsing), so a modern iPad may be reported as ``kind="mac"``. For our
    purposes that is fine: ``is_apple`` is still ``True`` — it is an Apple
    device either way, which is all the Reminders/Shortcuts flow needs.

    Args:
        user_agent: The raw ``User-Agent`` header, or ``None``.

    Returns:
        An :class:`AppleDevice`.
    """
    if not user_agent:
        return AppleDevice(is_apple=False, kind="unknown")

    ua = user_agent.lower()

    # Order matters: real iPod/iPad UAs contain "iPhone OS" (and "Mac OS X"),
    # so check the more specific tokens (ipod, ipad) before iphone/mac.
    if "ipod" in ua:
        return AppleDevice(is_apple=True, kind="ipod")
    if "ipad" in ua:
        return AppleDevice(is_apple=True, kind="ipad")
    if "iphone" in ua:
        return AppleDevice(is_apple=True, kind="iphone")
    if "macintosh" in ua or "mac os x" in ua:
        return AppleDevice(is_apple=True, kind="mac")

    return AppleDevice(is_apple=False, kind="unknown")


def reminder_entry_mode(user_agent: Optional[str]) -> str:
    """Return the reminder entry mode for a User-Agent.

    Args:
        user_agent: The raw ``User-Agent`` header, or ``None``.

    Returns:
        ``"apple"`` if :func:`detect_apple` reports an Apple platform, else
        ``"unknown"`` (also for ``None``/empty).
    """
    return "apple" if detect_apple(user_agent).is_apple else "unknown"


# --------------------------------------------------------------------------- #
# 3. Optional landing-page HTML helper
# --------------------------------------------------------------------------- #

_DEFAULT_LABELS = {
    "ru": {
        "title": "Добавить в Напоминания",
        "button": "📋 Добавить в Напоминания",
        "continue": "Продолжить",
        "warning": (
            "⚠️ Устройство Apple не обнаружено. Эта кнопка сработает, только "
            "если вы сейчас на устройстве Apple (Mac, iPhone или iPad). Если "
            "вы на нём — нажмите «Продолжить». Если нет — откройте эту "
            "страницу с устройства Apple."
        ),
    },
    "en": {
        "title": "Add to Reminders",
        "button": "📋 Add to Reminders",
        "continue": "Continue",
        "warning": (
            "⚠️ Apple device not detected. This button only works if you are "
            "currently on an Apple device (Mac, iPhone or iPad). If you are — "
            "tap “Continue”. If not — open this page from an Apple device."
        ),
    },
}


def reminder_landing_html(
    *,
    shortcut_url: str,
    mode: str,
    lang: str = "ru",
    labels: Optional[Mapping[str, str]] = None,
) -> str:
    """Render a self-contained HTML landing page for the Reminders button.

    This is an **optional convenience helper**. A project is free to render its
    own UI instead, using :func:`reminder_entry_mode` (to pick the state) and
    :func:`shortcuts_reminder_url` (for the link) directly.

    UX by ``mode``:
        * ``"apple"`` — Apple detected. The page shows the action as an
          explicit tool: a prominent **button** linking to ``shortcut_url``.
        * ``"unknown"`` — not detected. The page shows the **same button** as
          an option, plus a warning that it only works on an Apple device and
          the user may continue if they are on one.

    A small inline ``<script>`` re-checks the client's ``navigator`` on load;
    if it detects Apple there (client detection is more accurate than the
    server's User-Agent guess), it flips an ``"unknown"`` page into the
    explicit-tool state — closing the "we didn't detect it but you are on
    Apple" gap.

    Args:
        shortcut_url: The ``shortcuts://`` URL (from
            :func:`shortcuts_reminder_url`) the button opens.
        mode: ``"apple"`` or ``"unknown"`` (typically from
            :func:`reminder_entry_mode`). Any non-``"apple"`` value is treated
            as ``"unknown"``.
        lang: ``"ru"`` (default) or ``"en"`` — picks the default label set.
        labels: Optional overrides for any label keys: ``title``, ``button``,
            ``continue``, ``warning``.

    Returns:
        A complete, minimal, dependency-free HTML document as a string. All
        interpolated values are escaped.
    """
    base = _DEFAULT_LABELS.get(lang, _DEFAULT_LABELS["en"])
    text = dict(base)
    if labels:
        text.update(labels)

    is_apple = mode == "apple"

    # Escape everything that lands in HTML. The shortcut_url goes into an href
    # (quote=True escapes the double-quote that delimits the attribute).
    href = _escape(shortcut_url, quote=True)
    lbl_title = _escape(text["title"])
    lbl_button = _escape(text["button"])
    lbl_continue = _escape(text["continue"])
    lbl_warning = _escape(text["warning"])
    lang_attr = _escape(lang, quote=True)

    # Warning block is present in the DOM but hidden when Apple is detected;
    # the client script can un-hide/re-hide it.
    warning_style = "display:none;" if is_apple else ""
    button_label = lbl_button if is_apple else lbl_continue

    return f"""<!DOCTYPE html>
<html lang="{lang_attr}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{lbl_title}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
         margin: 0; padding: 2rem 1rem; background: #f5f5f7; color: #1d1d1f;
         display: flex; justify-content: center; }}
  .card {{ background: #fff; border-radius: 16px; padding: 2rem 1.5rem;
          max-width: 28rem; width: 100%; box-shadow: 0 2px 12px rgba(0,0,0,.08);
          text-align: center; }}
  h1 {{ font-size: 1.25rem; margin: 0 0 1.25rem; }}
  .warning {{ background: #fff8e1; border: 1px solid #ffe082; color: #6d4c00;
             border-radius: 12px; padding: .9rem 1rem; margin: 0 0 1.25rem;
             font-size: .95rem; line-height: 1.4; text-align: left; }}
  .btn {{ display: inline-block; background: #007aff; color: #fff;
         text-decoration: none; font-size: 1.05rem; font-weight: 600;
         padding: .85rem 1.5rem; border-radius: 12px; width: 100%;
         box-sizing: border-box; }}
  .btn:active {{ background: #0062cc; }}
</style>
</head>
<body>
  <div class="card">
    <h1>{lbl_title}</h1>
    <div class="warning" id="reminder-warning" style="{warning_style}">{lbl_warning}</div>
    <a class="btn" id="reminder-btn" href="{href}"
       data-label-tool="{lbl_button}" data-label-continue="{lbl_continue}">{button_label}</a>
  </div>
  <script>
    (function () {{
      var ua = navigator.userAgent || "";
      var plat = navigator.platform || "";
      var s = (ua + " " + plat).toLowerCase();
      var isApple = /iphone|ipad|ipod|macintosh|mac os x|macintel|macppc/.test(s) ||
                    (navigator.maxTouchPoints > 1 && /macintosh|macintel/.test(s));
      if (isApple) {{
        var warn = document.getElementById("reminder-warning");
        var btn = document.getElementById("reminder-btn");
        if (warn) {{ warn.style.display = "none"; }}
        if (btn) {{ btn.textContent = btn.getAttribute("data-label-tool"); }}
      }}
    }})();
  </script>
</body>
</html>"""
