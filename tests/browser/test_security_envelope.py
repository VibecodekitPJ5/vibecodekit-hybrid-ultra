"""Probe-#59 / #60 / #61 / #62 coverage — content-security helpers."""
from __future__ import annotations

import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[2]
SCRIPTS = KIT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from vibecodekit.browser import security  # noqa: E402


# ---- Probe #59 — envelope wrap -------------------------------------------

def test_wrap_untrusted_idempotent() -> None:
    raw = "Hello, world."
    wrapped = security.wrap_untrusted(raw)
    again = security.wrap_untrusted(wrapped)
    assert wrapped == again
    assert security.is_wrapped(wrapped)
    assert raw not in (security.ENVELOPE_OPEN, security.ENVELOPE_CLOSE)


def test_envelope_label_sanitised() -> None:
    out = security.wrap_untrusted("hi", label="bad label!! @#$ 1234567890123456789012345678901234567890")
    # Label should be stripped of unsafe chars and capped at 32.
    head_line = out.splitlines()[0]
    assert head_line.startswith(security.ENVELOPE_OPEN + "[label=")
    label = head_line.split("[label=", 1)[1].rstrip("]")
    assert len(label) <= 32
    assert all(c.isalnum() or c in "_-" for c in label)


def test_is_wrapped_negatives() -> None:
    assert security.is_wrapped("nope") is False
    assert security.is_wrapped("") is False


# ---- Probe #60 — hidden-element strip ------------------------------------

def test_strip_hidden_aria_hidden_subtree() -> None:
    tree = {
        "tag": "div",
        "attrs": {},
        "children": [
            {"tag": "span", "attrs": {"aria-hidden": "true"}, "text": "secret"},
            {"tag": "p",    "attrs": {}, "text": "visible"},
        ],
    }
    out = security.strip_hidden(tree)
    assert out is not None
    kids = out["children"]
    assert len(kids) == 1
    assert kids[0]["text"] == "visible"


def test_strip_hidden_display_none() -> None:
    tree = {"tag": "div", "attrs": {"style": "color: red; display: none;"}, "children": []}
    assert security.strip_hidden(tree) is None


def test_strip_hidden_visibility_hidden() -> None:
    tree = {"tag": "div", "attrs": {"style": "visibility:hidden"}, "children": []}
    assert security.strip_hidden(tree) is None


def test_strip_hidden_pass_through_for_non_dict() -> None:
    assert security.strip_hidden("just text") == "just text"
    assert security.strip_hidden(None) is None


# ---- Probe #61 — control-char / bidi sanitisation ------------------------

def test_sanitise_text_strips_rtl_override() -> None:
    payload = "Hello \u202EmaliciousRTL"
    cleaned = security.sanitise_text(payload)
    assert "\u202E" not in cleaned
    assert "Hello " in cleaned and "maliciousRTL" in cleaned


def test_sanitise_text_strips_zero_width_joiners() -> None:
    payload = "ad\u200bmin"
    assert security.sanitise_text(payload) == "admin"


def test_sanitise_text_preserves_safe_controls() -> None:
    payload = "line1\nline2\tcol2\rline3"
    assert security.sanitise_text(payload) == payload


def test_sanitise_text_non_string_pass_through() -> None:
    assert security.sanitise_text(42) == 42  # type: ignore[arg-type]


# ---- Probe #62 — URL blocklist -------------------------------------------

def test_classify_url_blocks_imds() -> None:
    v = security.classify_url("http://169.254.169.254/latest/meta-data/")
    assert v.allowed is False
    assert "private network" in v.reason or "169.254" in v.reason


def test_classify_url_blocks_metadata_host() -> None:
    v = security.classify_url("http://metadata.google.internal/")
    assert v.allowed is False
    assert "blocked host" in v.reason


def test_classify_url_blocks_dangerous_schemes() -> None:
    for url in ("file:///etc/passwd", "javascript:alert(1)", "chrome://flags",
                "data:text/html,<h1>x</h1>"):
        v = security.classify_url(url)
        assert v.allowed is False, f"expected blocked, got {v} for {url!r}"


def test_classify_url_allows_loopback() -> None:
    assert security.classify_url("http://localhost:3000").allowed is True
    assert security.classify_url("http://127.0.0.1:8000/health").allowed is True


def test_classify_url_allows_private_with_flag() -> None:
    v_default = security.classify_url("http://10.0.0.5:8080/")
    assert v_default.allowed is False
    v_explicit = security.classify_url("http://10.0.0.5:8080/", allow_private=True)
    assert v_explicit.allowed is True


def test_classify_url_allows_public() -> None:
    v = security.classify_url("https://example.com/")
    assert v.allowed is True
    assert v.reason == "public hostname"


def test_classify_url_rejects_empty_and_unparseable() -> None:
    assert security.classify_url("").allowed is False
    assert security.classify_url("ftp://ex.com").allowed is False
