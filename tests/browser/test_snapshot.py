"""Probes #59/#60 + snapshot diff hygiene."""
from __future__ import annotations

import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[2]
SCRIPTS = KIT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from vibecodekit.browser import security, snapshot  # noqa: E402


def test_hash_dom_stable_over_key_order() -> None:
    a = {"a": 1, "b": [1, 2], "c": {"x": 1, "y": 2}}
    b = {"c": {"y": 2, "x": 1}, "b": [1, 2], "a": 1}
    assert snapshot.hash_dom(a) == snapshot.hash_dom(b)


def test_hash_dom_changes_with_content() -> None:
    a = snapshot.hash_dom({"text": "Hello"})
    b = snapshot.hash_dom({"text": "Goodbye"})
    assert a != b


def test_normalise_aria_strips_hidden_subtree() -> None:
    tree = {
        "tag": "ul",
        "attrs": {},
        "children": [
            {"tag": "li", "attrs": {"aria-hidden": "true"}, "text": "secret"},
            {"tag": "li", "attrs": {}, "text": "visible \u202Eevil"},
        ],
    }
    cleaned = snapshot.normalise_aria(tree)
    assert cleaned is not None
    kids = cleaned["children"]
    assert len(kids) == 1
    # And the surviving li had its bidi-override stripped.
    assert "\u202E" not in kids[0]["text"]


def test_envelope_snapshot_wraps_text_field() -> None:
    snap = snapshot.Snapshot(
        url="https://example.com",
        title="Example",
        text="Hello, world.",
    )
    payload = snapshot.envelope_snapshot(snap)
    assert security.is_wrapped(payload["text"])
    assert payload["url"] == "https://example.com"


def test_diff_basic() -> None:
    s1 = snapshot.Snapshot(url="a", dom_hash="h1", captured_ts=100.0)
    s2 = snapshot.Snapshot(url="a", dom_hash="h2", console=[{"x": 1}], captured_ts=110.0)
    out = snapshot.diff(s1, s2)
    assert out["url_changed"] is False
    assert out["dom_changed"] is True
    assert out["new_console"] == 1
    assert out["elapsed_seconds"] == 10.0
