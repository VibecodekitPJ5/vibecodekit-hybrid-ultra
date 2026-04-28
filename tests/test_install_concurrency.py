"""v0.11.4 P3-1 regression: concurrent installers must serialise.

Stress-dipdive observation #P3-1 flagged that 3 parallel ``install``
calls into the same destination all did the full 251-file copy in
parallel.  After v0.11.4 the fcntl lock at
``<dst>/.vibecode/runtime/install.lock`` serialises them, so only the
first invocation performs creates; the rest re-plan against the
committed filesystem and report 100 % skips.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
PY = sys.executable


def test_three_parallel_installs_serialise_and_final_state_is_idempotent():
    dst = Path(tempfile.mkdtemp(prefix="vck_lock_"))
    try:
        env = {**os.environ, "PYTHONPATH": str(SCRIPTS)}
        t0 = time.time()
        procs = [
            subprocess.Popen(
                [PY, "-m", "vibecodekit.cli", "install", str(dst)],
                env=env,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True,
            )
            for _ in range(3)
        ]
        outs = [p.communicate(timeout=30) for p in procs]
        elapsed = time.time() - t0
        # All three must succeed.
        for i, p in enumerate(procs):
            assert p.returncode == 0, (
                f"parallel install {i} failed: rc={p.returncode} "
                f"stderr={outs[i][1][:300]!r}"
            )
        # Lock file must exist (created during at least one install).
        lock_path = dst / ".vibecode" / "runtime" / "install.lock"
        assert lock_path.exists(), "install lock file not created"
        # Final re-install must be fully idempotent.
        r = subprocess.run(
            [PY, "-m", "vibecodekit.cli", "install", str(dst)],
            env=env, capture_output=True, text=True, timeout=30,
        )
        assert r.returncode == 0, r
        payload = json.loads(r.stdout)
        assert payload["planned_creates"] == 0, (
            f"re-install has unexpected creates: {payload['planned_creates']}"
        )
        assert payload["planned_copies"] == 0, (
            f"re-install has unexpected overwrites: {payload['planned_copies']}"
        )
        assert payload["skipped"] >= 200, (
            f"re-install should skip most files: {payload['skipped']}"
        )
        # Serialisation should keep the whole thing under a reasonable budget.
        assert elapsed < 30.0, f"parallel install took {elapsed:.2f}s — too slow"
    finally:
        shutil.rmtree(dst, ignore_errors=True)


def test_dry_run_install_does_not_create_lock_file():
    dst = Path(tempfile.mkdtemp(prefix="vck_dry_"))
    try:
        r = subprocess.run(
            [PY, "-m", "vibecodekit.cli", "install", str(dst), "--dry-run"],
            env={**os.environ, "PYTHONPATH": str(SCRIPTS)},
            capture_output=True, text=True, timeout=30,
        )
        assert r.returncode == 0, r
        # dry-run should skip lock acquisition entirely (no .vibecode dir)
        lock_path = dst / ".vibecode" / "runtime" / "install.lock"
        assert not lock_path.exists(), (
            f"dry_run created a lock file: {lock_path}"
        )
    finally:
        shutil.rmtree(dst, ignore_errors=True)
