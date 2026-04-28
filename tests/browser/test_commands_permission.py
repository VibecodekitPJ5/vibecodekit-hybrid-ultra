"""Probe-#58 coverage — every browser command goes through permission_engine."""
from __future__ import annotations

import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[2]
SCRIPTS = KIT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from vibecodekit.browser import (  # noqa: E402
    commands_read,
    commands_write,
    permission as br_perm,
    security,
)


def _stub_runner_capture():
    """Return a stub runner + the list of (verb, target, extras) it observed."""
    seen: list[tuple] = []

    def runner(verb, target, extras):
        seen.append((verb, target, dict(extras)))
        return {"verb": verb, "ok": True}

    return runner, seen


def test_render_browser_command_canonical() -> None:
    out = br_perm.render_browser_command("goto", "https://example.com")
    assert out == "browser:goto https://example.com"
    out2 = br_perm.render_browser_command(
        "click", target=None, extras={"selector": "#login"})
    assert "browser:click" in out2
    assert "selector=" in out2


def test_render_browser_command_rejects_empty_verb() -> None:
    import pytest
    with pytest.raises(ValueError):
        br_perm.render_browser_command("")


def test_classify_returns_class_and_reason_tuple() -> None:
    klass, reason = br_perm.classify("goto", "https://example.com")
    assert klass in {"read_only", "verify", "mutation", "high_risk", "blocked"}
    assert isinstance(reason, str) and reason


def test_read_execute_calls_permission_then_runner() -> None:
    runner, seen = _stub_runner_capture()
    out = commands_read.execute("text", target=None, runner=runner)
    assert out["verb"] == "text"
    assert out["klass"] != "blocked"
    assert seen == [("text", None, {})]


def test_read_execute_envelope_wraps_untrusted_payload() -> None:
    def runner(verb, target, extras):
        return "raw page text including \u202EmaliciousRTL"
    out = commands_read.execute("text", runner=runner)
    payload = out["payload"]
    assert isinstance(payload, str)
    assert security.is_wrapped(payload)


def test_read_execute_status_is_not_wrapped() -> None:
    def runner(verb, target, extras):
        return {"tabs": ["default"], "active": "default"}
    out = commands_read.execute("status", runner=runner)
    assert out["payload"] == {"tabs": ["default"], "active": "default"}


def test_read_execute_unknown_verb_raises() -> None:
    import pytest
    with pytest.raises(ValueError):
        commands_read.execute("not-a-verb", runner=lambda *a: None)


def test_write_execute_blocks_imds_url() -> None:
    runner, seen = _stub_runner_capture()
    out = commands_write.execute("goto", "http://169.254.169.254/", runner=runner)
    assert out["klass"] == "blocked"
    assert seen == [], "runner must NOT be called when URL policy blocks (probe #58/#62)"


def test_write_execute_blocks_missing_url() -> None:
    out = commands_write.execute("goto", target=None, runner=lambda *a: None)
    assert out["klass"] == "blocked"
    assert "requires a URL" in out["reason"]


def test_write_execute_loopback_passes_to_runner() -> None:
    runner, seen = _stub_runner_capture()
    out = commands_write.execute("goto", "http://localhost:3000",
                                 runner=runner, allow_private=True)
    assert out["klass"] != "blocked"
    assert len(seen) == 1
    assert seen[0][0] == "goto"


def test_write_execute_unknown_verb_raises() -> None:
    import pytest
    with pytest.raises(ValueError):
        commands_write.execute("xxx", runner=lambda *a: None)


def test_write_execute_high_risk_set_cookie_still_classified() -> None:
    runner, seen = _stub_runner_capture()
    out = commands_write.execute(
        "set_cookie", target=None,
        extras={"name": "session", "value": "x", "url": "https://example.com"},
        runner=runner,
    )
    # Whatever the verdict, the runner must be called only if not blocked.
    if out["klass"] == "blocked":
        assert seen == []
    else:
        assert len(seen) == 1
