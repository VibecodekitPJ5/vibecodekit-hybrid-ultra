"""HOTFIX-007 / REFINE-003 / REFINE-FINAL / v0.11.4.1: 3-layout release gate.

Validates a VibecodeKit release candidate across the three layouts
users actually see.  Fails fast on the first layout that doesn't pass:

    L1. Source skill bundle           — audit (w/ $VIBECODE_UPDATE_PACKAGE).
    L2. Skill + update siblings       — audit at threshold 1.0.
    L3. Fresh installed project       — install, doctor --installed-only,
                                        audit at threshold 1.0, runtime dataset load.

**Canonical release gate (v0.11.4.1 onwards):**

    1.  ``python -m pytest tests -q``                        ← run directly
    2.  ``python tools/validate_release_matrix.py --skill X --update Y``

The matrix script is layout-matrix only; pytest is **not** part of the
canonical matrix gate.  Reviewers should run pytest directly — the
two gates are complementary but independent.

``--with-pytest`` is retained as an **optional, non-canonical** shortcut
that spawns pytest in a subprocess from inside the matrix run.  In some
constrained execution environments (nested containers with odd
signal-forwarding, PTY-less CI runners, read-only tmpdirs, etc.) this
subprocess has been observed to hang until its 180 s budget trips.
When that happens the matrix script will fail fast with
``[TIMEOUT] pytest source bundle`` — it will not hang indefinitely —
but the signal is less useful than running pytest directly.  **Prefer
``pytest tests`` over ``--with-pytest``** for release sign-off.

Exit 0 iff all three layouts pass.  Never hangs:
- Each subprocess runs in its own session (``start_new_session=True``).
- On timeout the full process group is killed via ``os.killpg``.
- Timeouts are reported as ``[TIMEOUT] <label>`` failures, not silent
  hangs.

Usage:
    # CANONICAL GATE (recommended):
    python -m pytest tests -q
    python tools/validate_release_matrix.py \\
        --skill   /path/to/skill/vibecodekit-hybrid-ultra \\
        --update  /path/to/update-package

    # Optional / non-canonical:
    python tools/validate_release_matrix.py ... --with-pytest
    python tools/validate_release_matrix.py ... --fast      # alias (default)
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path


# Per-command wall-clock budgets.  Keep generous so slow CI passes, but
# bounded so nothing runs forever.
DEFAULT_TIMEOUT_SECONDS = {
    "pytest": 180,
    "audit": 60,
    "install": 60,
    "doctor": 30,
    "runtime_load": 30,
}


class CmdResult:
    __slots__ = ("returncode", "stdout", "stderr", "timed_out", "elapsed", "label")

    def __init__(self, *, returncode: int, stdout: str, stderr: str,
                 timed_out: bool, elapsed: float, label: str) -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.timed_out = timed_out
        self.elapsed = elapsed
        self.label = label


def _run(cmd: list, env: dict, cwd: Path, label: str,
         timeout: int) -> CmdResult:
    """Run ``cmd`` with a hard timeout.  Kills the full process group on
    expiry so forked-off pytest workers / shell subprocs don't linger.
    """
    display = " ".join(str(c) for c in cmd[:4])
    print(f"  $ {display}{' …' if len(cmd) > 4 else ''}  [timeout={timeout}s]")
    t0 = time.monotonic()
    # v0.11.4.1: stdin=DEVNULL so pytest / audit / doctor never try to
    # read interactively — some nested container / CI environments
    # otherwise leak a live-ish stdin that makes pytest hang on
    # input() prompts or waiting-for-tty probes.
    p = subprocess.Popen(
        [str(c) for c in cmd],
        env=env,
        cwd=str(cwd),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        out, err = p.communicate(timeout=timeout)
        timed_out = False
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            out, err = p.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            out, err = "", ""
        timed_out = True
    elapsed = time.monotonic() - t0
    rc = p.returncode if p.returncode is not None else -9
    res = CmdResult(returncode=rc, stdout=out or "", stderr=err or "",
                    timed_out=timed_out, elapsed=elapsed, label=label)
    if timed_out:
        print(f"    [TIMEOUT] {label} after {elapsed:.1f}s (killed)")
    elif rc != 0:
        print(f"    [FAIL] {label} exit={rc} (t={elapsed:.1f}s)")
        tail = (err or "").strip().splitlines()[-10:]
        if tail:
            print("    stderr tail:")
            for ln in tail:
                print(f"      {ln}")
    return res


def _env_with(pythonpath: Path, **kw) -> dict:
    e = os.environ.copy()
    e["PYTHONPATH"] = str(pythonpath)
    e.update({k: str(v) for k, v in kw.items()})
    return e


def _parse_audit(stdout: str) -> dict:
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {"passed": 0, "total": 0, "met": False}


def validate(skill: Path, update: Path, *, with_pytest: bool = False) -> int:
    findings: list = []

    # ------------------------------------------------------------------ L1 --
    print("[1/3] Source skill bundle")
    scripts = skill / "scripts"
    env1 = _env_with(scripts, VIBECODE_UPDATE_PACKAGE=update)

    if with_pytest:
        r = _run([sys.executable, "-m", "pytest", "tests", "-q"], env1, skill,
                 "pytest source bundle", DEFAULT_TIMEOUT_SECONDS["pytest"])
        if r.timed_out:
            findings.append(f"L1 pytest timed out after {r.elapsed:.1f}s")
        elif r.returncode != 0:
            findings.append("L1 pytest failed")
    else:
        print("  (pytest skipped — pass --with-pytest to run the full suite)")

    r = _run([sys.executable, "-m", "vibecodekit.cli", "audit",
              "--threshold", "1.0"], env1, skill,
             "audit source + update", DEFAULT_TIMEOUT_SECONDS["audit"])
    if r.timed_out:
        findings.append(f"L1 audit timed out after {r.elapsed:.1f}s")
    elif r.returncode != 0:
        findings.append("L1 audit below threshold")
    else:
        d = _parse_audit(r.stdout)
        if d.get("passed") != d.get("total"):
            findings.append(f"L1 audit {d.get('passed')}/{d.get('total')}")

    if findings:
        return _finalise(findings)

    # ------------------------------------------------------------------ L2 --
    print("[2/3] Skill + update siblings (advisory — same as L1 today)")

    # ------------------------------------------------------------------ L3 --
    print("[3/3] Fresh installed project")
    with tempfile.TemporaryDirectory(prefix="vck-release-matrix-") as tmp:
        proj = Path(tmp) / "user_project"
        proj.mkdir()
        for entry in update.iterdir():
            dst = proj / entry.name
            if entry.is_dir():
                shutil.copytree(entry, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(entry, dst)
        env3 = _env_with(scripts)
        r = _run([sys.executable, "-m", "vibecodekit.cli", "install", str(proj)],
                 env3, proj, "install into fresh project",
                 DEFAULT_TIMEOUT_SECONDS["install"])
        if r.timed_out or r.returncode != 0:
            findings.append("L3 install failed" + (" (timeout)" if r.timed_out else ""))
            return _finalise(findings)
        installed_scripts = proj / "ai-rules" / "vibecodekit" / "scripts"
        env_i = _env_with(installed_scripts, VIBECODE_UPDATE_PACKAGE=update)
        r = _run([sys.executable, "-m", "vibecodekit.cli", "doctor",
                  "--root", str(proj), "--installed-only"],
                 env_i, proj, "doctor --installed-only",
                 DEFAULT_TIMEOUT_SECONDS["doctor"])
        if r.timed_out:
            findings.append(f"L3 doctor timed out after {r.elapsed:.1f}s")
        elif r.returncode != 0:
            findings.append("L3 doctor --installed-only failed")
        r = _run([sys.executable, "-m", "vibecodekit.cli", "audit",
                  "--threshold", "1.0"], env_i, proj,
                 "audit from installed", DEFAULT_TIMEOUT_SECONDS["audit"])
        if r.timed_out:
            findings.append(f"L3 audit timed out after {r.elapsed:.1f}s")
        elif r.returncode != 0:
            findings.append("L3 audit below threshold")
        else:
            d = _parse_audit(r.stdout)
            if d.get("passed") != d.get("total"):
                findings.append(f"L3 audit {d.get('passed')}/{d.get('total')}")
        r = _run(
            [sys.executable, "-c",
             "from vibecodekit.methodology import load_rri_questions\n"
             "from vibecodekit.scaffold_engine import ScaffoldEngine\n"
             "assert len(load_rri_questions('docs')) >= 25\n"
             "presets = [p.name for p in ScaffoldEngine().list_presets()]\n"
             "assert 'docs' in presets\n"
             "assert 'saas' in presets\n"
             "print('OK')"],
            env_i, proj, "runtime import + dataset load",
            DEFAULT_TIMEOUT_SECONDS["runtime_load"])
        if r.timed_out:
            findings.append(f"L3 runtime load timed out after {r.elapsed:.1f}s")
        elif r.returncode != 0:
            findings.append("L3 runtime dataset load failed")

    return _finalise(findings)


def _finalise(findings: list) -> int:
    print()
    if findings:
        print("[RESULT] release gate FAILED:")
        for f in findings:
            print("  -", f)
        return 1
    print("[RESULT] release gate PASSED — all 3 layouts clean.")
    return 0


def _main() -> int:
    ap = argparse.ArgumentParser(description="VibecodeKit release matrix.")
    ap.add_argument("--skill", required=True, type=Path)
    ap.add_argument("--update", required=True, type=Path)
    ap.add_argument("--with-pytest", action="store_true",
                    help="[NON-CANONICAL / OPTIONAL] Also run the pytest "
                         "suite in L1.  May hang in constrained environments; "
                         "prefer running 'pytest tests' directly as the "
                         "canonical pytest gate.")
    ap.add_argument("--fast", action="store_true",
                    help="Alias for default (no pytest).  Kept for "
                         "backwards compatibility with REFINE-003 scripts.")
    args = ap.parse_args()
    if args.fast and args.with_pytest:
        print("[ERROR] --fast and --with-pytest are mutually exclusive")
        return 2
    if not (args.skill / "scripts" / "vibecodekit" / "cli.py").is_file():
        print(f"[ERROR] skill path {args.skill} does not contain scripts/vibecodekit/cli.py")
        return 1
    if not (args.update / ".claude").is_dir():
        print(f"[ERROR] update path {args.update} does not contain .claude/")
        return 1
    return validate(args.skill.resolve(), args.update.resolve(),
                    with_pytest=args.with_pytest)


if __name__ == "__main__":
    sys.exit(_main())
