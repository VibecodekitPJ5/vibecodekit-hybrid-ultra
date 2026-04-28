"""v0.11.4 P3-2 regression: CLI error hygiene for `install` / `scaffold`.

Unhappy paths used to emit raw Python tracebacks.  After v0.11.4 they
must emit a JSON diagnostic on stderr with a non-zero exit code — no
traceback, no secrets leaked, no internal paths.
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO                           # this test file lives inside the skill bundle
SCRIPTS = SKILL / "scripts"

PY = sys.executable


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [PY, "-m", "vibecodekit.cli", *args],
        env={**os.environ, "PYTHONPATH": str(SCRIPTS)},
        capture_output=True, text=True, timeout=30,
    )


@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason=(
        "root bypasses POSIX DAC chmod permissions, so chmod 0400 on a "
        "temp dir does not prevent writes.  The 'file-where-dir' test "
        "below covers the same surface (clean JSON error instead of "
        "traceback) in a way that works deterministically for both "
        "root and non-root users."
    ),
)
def test_install_into_readonly_dir_emits_clean_json_error():
    ro_root = Path(tempfile.mkdtemp(prefix="vck_ro_"))
    try:
        os.chmod(ro_root, stat.S_IRUSR | stat.S_IXUSR)  # no write
        r = _run_cli("install", str(ro_root / "sub"))
        assert r.returncode == 1, r
        # No traceback leaked to stdout/stderr
        assert "Traceback" not in r.stderr, r.stderr
        # Clean JSON on stderr
        payload = json.loads(r.stderr)
        assert payload.get("error") in {
            "PermissionError", "OSError",
        }, payload
        assert payload.get("destination", "").endswith("/sub"), payload
    finally:
        os.chmod(ro_root, 0o755)
        shutil.rmtree(ro_root, ignore_errors=True)


def test_install_into_file_where_dir_expected_emits_clean_json_error():
    td = Path(tempfile.mkdtemp(prefix="vck_fd_"))
    try:
        file_path = td / "iam_a_file"
        file_path.write_text("not a directory", encoding="utf-8")
        # install tries to place files under iam_a_file/ — should fail cleanly
        r = _run_cli("install", str(file_path))
        assert r.returncode == 1, r
        assert "Traceback" not in r.stderr, r.stderr
        payload = json.loads(r.stderr)
        # NotADirectoryError, FileExistsError, or generic OSError all acceptable
        assert payload.get("error") in {
            "NotADirectoryError", "FileExistsError", "OSError",
        }, payload
    finally:
        shutil.rmtree(td, ignore_errors=True)


def test_scaffold_unknown_preset_emits_clean_json_error():
    td = Path(tempfile.mkdtemp(prefix="vck_sp_"))
    try:
        # preset is positional, stack is --stack
        r = _run_cli("scaffold", "preview", "nonexistent-preset",
                     "--stack", "nextjs", "--target-dir", str(td))
        assert r.returncode == 1, r
        assert "Traceback" not in r.stderr, r.stderr
        payload = json.loads(r.stderr)
        # scaffold_engine may raise FileNotFoundError (OSError subclass)
        # or ValueError depending on which validation fires first; both
        # must reach the CLI guard as a clean JSON diagnostic.
        assert payload.get("error") in {"ValueError", "OSError",
                                        "FileNotFoundError"}, payload
        assert "nonexistent-preset" in payload.get("message", ""), payload
    finally:
        shutil.rmtree(td, ignore_errors=True)


def test_scaffold_unknown_stack_emits_clean_json_error():
    td = Path(tempfile.mkdtemp(prefix="vck_ss_"))
    try:
        r = _run_cli("scaffold", "preview", "docs",
                     "--stack", "totally-made-up-stack", "--target-dir", str(td))
        # Either ValueError (stack validation) or exit 1 with clean JSON.
        assert r.returncode == 1, r
        assert "Traceback" not in r.stderr, r.stderr
        payload = json.loads(r.stderr)
        assert payload.get("error") in {"ValueError", "OSError",
                                        "FileNotFoundError"}, payload
    finally:
        shutil.rmtree(td, ignore_errors=True)
