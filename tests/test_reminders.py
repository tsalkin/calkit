"""Tests for the Apple Reminders / Shortcuts helpers."""

from __future__ import annotations

import datetime as dt
import json
from urllib.parse import parse_qs, unquote, urlparse
from zoneinfo import ZoneInfo

import pytest

from calkit import (
    AppleDevice,
    detect_apple,
    reminder_entry_mode,
    reminder_landing_html,
    shortcuts_reminder_url,
)


# --------------------------------------------------------------------------- #
# shortcuts_reminder_url
# --------------------------------------------------------------------------- #

def _payload_from_url(url: str) -> dict:
    """Extract and JSON-parse the `input` param back into a dict."""
    assert url.startswith("shortcuts://run-shortcut?")
    q = parse_qs(urlparse(url).query)
    return json.loads(q["input"][0])


def test_shortcuts_url_scheme_and_name_encoding():
    url = shortcuts_reminder_url(name="Add Reminder", title="Buy milk")
    assert url.startswith("shortcuts://run-shortcut?")
    q = parse_qs(urlparse(url).query)
    assert q["name"] == ["Add Reminder"]
    # Space must be percent-encoded, not left raw or turned into '+'.
    assert "name=Add%20Reminder" in url


def test_shortcuts_url_payload_roundtrip_fixed_keys():
    payload = _payload_from_url(
        shortcuts_reminder_url(
            name="Add Reminder",
            title="Call dentist",
            notes="Bring insurance card",
            url="https://example.com/booking/42",
        )
    )
    assert payload["title"] == "Call dentist"
    assert payload["notes"] == "Bring insurance card"
    assert payload["url"] == "https://example.com/booking/42"
    assert payload["due"] is None
    # All four fixed keys always present.
    assert set(payload) == {"title", "due", "notes", "url"}


def test_shortcuts_url_defaults_are_none():
    payload = _payload_from_url(shortcuts_reminder_url(name="S", title="T"))
    assert payload == {"title": "T", "due": None, "notes": None, "url": None}


def test_shortcuts_url_compact_json_no_spaces():
    url = shortcuts_reminder_url(name="S", title="T")
    raw = unquote(parse_qs(urlparse(url).query)["input"][0])
    assert ", " not in raw and '": ' not in raw  # separators=(",", ":")


def test_shortcuts_url_due_naive_datetime_localized_to_tz():
    payload = _payload_from_url(
        shortcuts_reminder_url(
            name="S",
            title="T",
            due=dt.datetime(2026, 7, 1, 15, 0),
            tz="Europe/Berlin",
        )
    )
    parsed = dt.datetime.fromisoformat(payload["due"])
    assert parsed.tzinfo is not None
    # Berlin in July = +02:00 (CEST).
    assert parsed.utcoffset() == dt.timedelta(hours=2)
    assert parsed.replace(tzinfo=None) == dt.datetime(2026, 7, 1, 15, 0)


def test_shortcuts_url_due_aware_datetime_kept():
    aware = dt.datetime(2026, 7, 1, 9, 0, tzinfo=ZoneInfo("America/New_York"))
    payload = _payload_from_url(
        shortcuts_reminder_url(name="S", title="T", due=aware, tz="UTC")
    )
    parsed = dt.datetime.fromisoformat(payload["due"])
    # -04:00 EDT in July; the aware zone wins over tz="UTC".
    assert parsed.utcoffset() == dt.timedelta(hours=-4)


def test_shortcuts_url_due_string_passthrough():
    payload = _payload_from_url(
        shortcuts_reminder_url(name="S", title="T", due="2026-07-01T10:00:00Z")
    )
    assert payload["due"] == "2026-07-01T10:00:00Z"


def test_shortcuts_url_due_date():
    payload = _payload_from_url(
        shortcuts_reminder_url(name="S", title="T", due=dt.date(2026, 7, 4))
    )
    assert payload["due"] == "2026-07-04"


def test_shortcuts_url_extra_fields_merged():
    payload = _payload_from_url(
        shortcuts_reminder_url(
            name="S",
            title="T",
            shortcut_input_extra={"list": "Work", "priority": 1},
        )
    )
    assert payload["list"] == "Work"
    assert payload["priority"] == 1
    assert payload["title"] == "T"


def test_shortcuts_url_non_ascii_and_special_chars_encode():
    url = shortcuts_reminder_url(
        name="Список & дела",
        title="Купить молоко / хлеб?",
        notes="заметка: строка",
    )
    # Reserved / non-ASCII chars must not appear raw inside the param VALUES
    # (the single '&'/'?' that structure the URL are fine).
    query = urlparse(url).query
    name_val = query.split("name=", 1)[1].split("&", 1)[0]
    input_val = query.split("input=", 1)[1]
    for value in (name_val, input_val):
        for bad in ["&", "?", " ", "Список", "молоко"]:
            assert bad not in value
    # But everything round-trips.
    q = parse_qs(urlparse(url).query)
    assert q["name"] == ["Список & дела"]
    payload = json.loads(q["input"][0])
    assert payload["title"] == "Купить молоко / хлеб?"
    assert payload["notes"] == "заметка: строка"


def test_shortcuts_url_invalid_due_type_raises():
    with pytest.raises(TypeError):
        shortcuts_reminder_url(name="S", title="T", due=12345)


# --------------------------------------------------------------------------- #
# detect_apple
# --------------------------------------------------------------------------- #

_IPHONE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
)
_IPAD_UA = (
    "Mozilla/5.0 (iPad; CPU OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
)
_IPOD_UA = (
    "Mozilla/5.0 (iPod touch; CPU iPhone OS 15_8 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
)
_MAC_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.5 Safari/605.1.15"
)
_WINDOWS_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)
_ANDROID_UA = (
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0 Mobile Safari/537.36"
)


def test_detect_apple_iphone():
    d = detect_apple(_IPHONE_UA)
    assert d == AppleDevice(is_apple=True, kind="iphone")


def test_detect_apple_ipad():
    d = detect_apple(_IPAD_UA)
    assert d == AppleDevice(is_apple=True, kind="ipad")


def test_detect_apple_ipod():
    d = detect_apple(_IPOD_UA)
    assert d == AppleDevice(is_apple=True, kind="ipod")


def test_detect_apple_mac():
    d = detect_apple(_MAC_UA)
    assert d == AppleDevice(is_apple=True, kind="mac")


def test_detect_apple_windows():
    d = detect_apple(_WINDOWS_UA)
    assert d == AppleDevice(is_apple=False, kind="unknown")


def test_detect_apple_android():
    d = detect_apple(_ANDROID_UA)
    assert d == AppleDevice(is_apple=False, kind="unknown")


def test_detect_apple_none_and_empty():
    assert detect_apple(None) == AppleDevice(is_apple=False, kind="unknown")
    assert detect_apple("") == AppleDevice(is_apple=False, kind="unknown")


def test_detect_apple_iphone_takes_priority_over_mac_os_x_substring():
    # iPhone UAs contain "like Mac OS X" — must still be iphone, not mac.
    assert detect_apple(_IPHONE_UA).kind == "iphone"


# --------------------------------------------------------------------------- #
# reminder_entry_mode
# --------------------------------------------------------------------------- #

def test_reminder_entry_mode_apple():
    assert reminder_entry_mode(_IPHONE_UA) == "apple"
    assert reminder_entry_mode(_MAC_UA) == "apple"


def test_reminder_entry_mode_unknown():
    assert reminder_entry_mode(_WINDOWS_UA) == "unknown"
    assert reminder_entry_mode(_ANDROID_UA) == "unknown"


def test_reminder_entry_mode_none():
    assert reminder_entry_mode(None) == "unknown"


# --------------------------------------------------------------------------- #
# reminder_landing_html
# --------------------------------------------------------------------------- #

def test_landing_apple_has_button_and_link_no_warning():
    url = shortcuts_reminder_url(name="Add Reminder", title="T")
    html = reminder_landing_html(shortcut_url=url, mode="apple")
    assert "<html" in html and "</html>" in html
    # Button links to the shortcut url.
    assert 'id="reminder-btn"' in html
    assert "shortcuts://run-shortcut" in html
    # Warning block exists but is hidden in apple mode.
    assert 'id="reminder-warning"' in html
    assert "display:none;" in html


def test_landing_unknown_has_button_link_and_visible_warning():
    url = shortcuts_reminder_url(name="Add Reminder", title="T")
    html = reminder_landing_html(shortcut_url=url, mode="unknown")
    assert 'id="reminder-btn"' in html
    assert "shortcuts://run-shortcut" in html
    # Warning text present (ru default) and its block not force-hidden.
    assert "не обнаружено" in html
    # The warning div should not carry the inline hide style in unknown mode.
    assert '<div class="warning" id="reminder-warning" style="">' in html


def test_landing_lang_en():
    url = shortcuts_reminder_url(name="S", title="T")
    html = reminder_landing_html(shortcut_url=url, mode="unknown", lang="en")
    assert "Apple device not detected" in html
    assert "Add to Reminders" in html


def test_landing_labels_override():
    url = shortcuts_reminder_url(name="S", title="T")
    html = reminder_landing_html(
        shortcut_url=url,
        mode="apple",
        labels={"button": "MY BUTTON", "title": "MY TITLE"},
    )
    assert "MY BUTTON" in html
    assert "MY TITLE" in html


def test_landing_escapes_injected_values():
    # A crafted shortcut_url with a quote must not break out of the href.
    url = 'shortcuts://run-shortcut?name="x"&input=<script>alert(1)</script>'
    html = reminder_landing_html(shortcut_url=url, mode="apple")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
    # Injected label with markup is escaped too.
    html2 = reminder_landing_html(
        shortcut_url="shortcuts://x",
        mode="apple",
        labels={"title": "<b>hi</b>"},
    )
    assert "<b>hi</b>" not in html2
    assert "&lt;b&gt;hi&lt;/b&gt;" in html2


def test_landing_has_client_detection_script():
    html = reminder_landing_html(shortcut_url="shortcuts://x", mode="unknown")
    assert "<script>" in html
    assert "navigator" in html
    assert "maxTouchPoints" in html  # iPadOS-masquerade handling
