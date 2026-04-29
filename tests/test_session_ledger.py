"""Tests for vibecodekit.session_ledger (v0.15.0-alpha — T1)."""
from __future__ import annotations

import json
import subprocess
import sys
import threading
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
PYTHON = sys.executable


def _run(args, cwd: Path):
    return subprocess.run(
        [PYTHON, "-m", *args],
        cwd=str(cwd),
        env={"PYTHONPATH": str(REPO / "scripts"),
             "PATH": "/usr/bin:/bin"},
        capture_output=True, text=True, check=False, timeout=15,
    )


def test_record_then_read(tmp_path):
    from vibecodekit.session_ledger import record_gate, gates_run
    record_gate("/vck-review", root=tmp_path)
    record_gate("/vck-qa-only", root=tmp_path)
    assert gates_run(root=tmp_path) == ["/vck-review", "/vck-qa-only"]


def test_clear_when_present_and_missing(tmp_path):
    from vibecodekit.session_ledger import record_gate, gates_run, clear
    clear(root=tmp_path)  # missing — no error
    record_gate("/vck-review", root=tmp_path)
    assert gates_run(root=tmp_path) == ["/vck-review"]
    clear(root=tmp_path)
    assert gates_run(root=tmp_path) == []


def test_corrupt_line_skipped(tmp_path):
    from vibecodekit.session_ledger import gates_run, ledger_path
    p = ledger_path(root=tmp_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        '{"gate": "/vck-review", "ts": 1.0}\n'
        'GARBAGE-LINE-{not-json}\n'
        '\n'
        '{"gate": "/vck-qa-only", "ts": 2.0}\n',
        encoding="utf-8",
    )
    assert gates_run(root=tmp_path) == ["/vck-review", "/vck-qa-only"]


def test_record_drops_reserved_keys(tmp_path):
    from vibecodekit.session_ledger import record_gate, ledger_path
    record_gate("/vck-review", root=tmp_path,
                extra={"gate": "evil", "ts": -1, "actor": "alice"})
    line = ledger_path(root=tmp_path).read_text(encoding="utf-8").strip()
    row = json.loads(line)
    assert row["gate"] == "/vck-review"  # not "evil"
    assert row["ts"] != -1
    assert row["actor"] == "alice"


def test_concurrent_appends_no_corruption(tmp_path):
    from vibecodekit.session_ledger import record_gate, gates_run
    N_THREADS = 8
    PER_THREAD = 12

    def worker(name: str):
        for i in range(PER_THREAD):
            record_gate(f"/vck-{name}-{i}", root=tmp_path)

    threads = [
        threading.Thread(target=worker, args=(f"t{n}",))
        for n in range(N_THREADS)
    ]
    for t in threads: t.start()
    for t in threads: t.join()

    gates = gates_run(root=tmp_path)
    assert len(gates) == N_THREADS * PER_THREAD
    # Every recorded gate name must be parseable (no truncated JSON).
    for g in gates:
        assert g.startswith("/vck-")


# ---------------------------------------------------------------------------
# CLI smoke tests via team_mode subcommands.
# ---------------------------------------------------------------------------

def test_team_mode_record_check_clear_cli(tmp_path):
    # No team config → check is no-op.
    r = _run(["vibecodekit.team_mode", "check"], cwd=tmp_path)
    assert r.returncode == 0
    assert "skipping" in r.stdout.lower() or r.stdout == ""

    # Record one gate.
    r = _run(["vibecodekit.team_mode", "record", "--gate", "/vck-review"],
             cwd=tmp_path)
    assert r.returncode == 0
    row = json.loads(r.stdout.strip())
    assert row["gate"] == "/vck-review"

    # Init team config requiring 2 gates.
    r = _run(["vibecodekit.team_mode", "init",
              "--team-id", "x",
              "--required", "/vck-review",
              "--required", "/vck-qa-only"],
             cwd=tmp_path)
    assert r.returncode == 0

    # Now check: only /vck-review recorded → violation.
    r = _run(["vibecodekit.team_mode", "check"], cwd=tmp_path)
    assert r.returncode == 2
    assert "/vck-qa-only" in r.stderr

    # Record the missing one.
    _run(["vibecodekit.team_mode", "record", "--gate", "/vck-qa-only"],
         cwd=tmp_path)
    r = _run(["vibecodekit.team_mode", "check"], cwd=tmp_path)
    assert r.returncode == 0

    # Clear.
    r = _run(["vibecodekit.team_mode", "clear"], cwd=tmp_path)
    assert r.returncode == 0
    # Now check would fail again.
    r = _run(["vibecodekit.team_mode", "check"], cwd=tmp_path)
    assert r.returncode == 2


def test_team_mode_check_gates_run_arg(tmp_path):
    """``--gates-run`` overrides the ledger entirely."""
    _run(["vibecodekit.team_mode", "init",
          "--team-id", "x", "--required", "/vck-review"], cwd=tmp_path)
    # Empty ledger but pass via arg.
    r = _run(["vibecodekit.team_mode", "check",
              "--gates-run", "/vck-review,/vck-qa-only"],
             cwd=tmp_path)
    assert r.returncode == 0
    # Wrong arg.
    r = _run(["vibecodekit.team_mode", "check",
              "--gates-run", "/vck-foo"], cwd=tmp_path)
    assert r.returncode == 2
