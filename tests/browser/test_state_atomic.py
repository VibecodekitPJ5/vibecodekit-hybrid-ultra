"""Probe-#54 / #55 / #57 coverage — atomic state file behaviour."""
from __future__ import annotations

import json
import os
import stat
import sys
import time
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[2]
SCRIPTS = KIT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from vibecodekit.browser import state as state_mod  # noqa: E402


def _state_path(tmp_path: Path) -> Path:
    return tmp_path / ".vibecode" / "browser.json"


def test_state_path_under_home(tmp_path: Path) -> None:
    p = state_mod.state_path(home=tmp_path)
    assert p == tmp_path / ".vibecode" / "browser.json"


def test_write_state_creates_0o600_file(tmp_path: Path) -> None:
    target = _state_path(tmp_path)
    s = state_mod.BrowserState(pid=os.getpid(), port=12345)
    state_mod.write_state(s, path=target)
    assert target.exists()
    mode = stat.S_IMODE(os.stat(target).st_mode)
    assert mode == 0o600, f"state file should be 0o600 (probe #54), got 0o{mode:o}"


def test_write_state_atomic_no_partial_file(tmp_path: Path, monkeypatch) -> None:
    """Probe #54: simulated crash leaves the previous content intact."""
    target = _state_path(tmp_path)
    s = state_mod.BrowserState(pid=11, port=10101)
    state_mod.write_state(s, path=target)
    original = target.read_text(encoding="utf-8")

    def _boom(*_a, **_k):
        raise RuntimeError("simulated crash mid-write")

    monkeypatch.setattr(state_mod.os, "replace", _boom)
    with pytest.raises(RuntimeError):
        state_mod.write_state(state_mod.BrowserState(pid=22, port=20202), path=target)
    # The target must still contain the original content (no partial write).
    assert target.read_text(encoding="utf-8") == original
    # And no leftover .tmp files in the directory.
    leftovers = [p for p in target.parent.iterdir()
                 if p.name.startswith(".browser.") and p.suffix == ".tmp"]
    assert leftovers == [], f"tmp file leaked: {leftovers}"


def test_default_idle_timeout_is_30_minutes() -> None:
    """Probe #55."""
    assert state_mod.DEFAULT_IDLE_TIMEOUT_SECONDS == 30 * 60


def test_is_idle_expired() -> None:
    s = state_mod.BrowserState(
        pid=os.getpid(), port=1,
        last_activity_ts=time.time() - 60,
        idle_timeout_seconds=10,
    )
    assert state_mod.is_idle_expired(s) is True
    s2 = state_mod.BrowserState(
        pid=os.getpid(), port=1,
        last_activity_ts=time.time(),
        idle_timeout_seconds=300,
    )
    assert state_mod.is_idle_expired(s2) is False


def test_touch_state_bumps_activity(tmp_path: Path) -> None:
    target = _state_path(tmp_path)
    s = state_mod.BrowserState(pid=os.getpid(), port=1, last_activity_ts=100.0)
    state_mod.write_state(s, path=target)
    state_mod.touch_state(path=target, now=200.0)
    re = state_mod.read_state(path=target)
    assert re is not None
    assert re.last_activity_ts == 200.0


def test_cookie_path_round_trips(tmp_path: Path) -> None:
    """Probe #57."""
    target = _state_path(tmp_path)
    s = state_mod.BrowserState(
        pid=os.getpid(), port=1,
        cookie_path="/home/u/.vibecode/cookies.json",
    )
    state_mod.write_state(s, path=target)
    re = state_mod.read_state(path=target)
    assert re is not None
    assert re.cookie_path == "/home/u/.vibecode/cookies.json"


def test_select_port_in_range() -> None:
    port = state_mod.select_port()
    low, high = state_mod.PORT_RANGE
    assert low <= port < high


def test_clear_state_idempotent(tmp_path: Path) -> None:
    target = _state_path(tmp_path)
    state_mod.write_state(state_mod.BrowserState(pid=1, port=1), path=target)
    assert state_mod.clear_state(path=target) is True
    assert state_mod.clear_state(path=target) is False


def test_corrupt_state_returns_none(tmp_path: Path) -> None:
    target = _state_path(tmp_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("not json", encoding="utf-8")
    assert state_mod.read_state(path=target) is None


def test_is_pid_alive_self() -> None:
    assert state_mod.is_pid_alive(os.getpid()) is True
    assert state_mod.is_pid_alive(0) is False
    assert state_mod.is_pid_alive(-1) is False
