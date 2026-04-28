"""End-to-end install integration test — v0.10.3.

Exercises a fresh-install flow (as a new user would experience):

    1. Create an empty temp directory.
    2. Install the overlay into it via ``vibe install``.
    3. Run the conformance audit from the installed location → expect 39/39.
    4. Run a sample plan end-to-end → expect ``plan_exhausted`` terminal.
    5. Run the permission engine on a known-dangerous command → ``deny``.
    6. Register an MCP server in-process and call a tool → ``pong``.
    7. Round-trip the approval contract (create → respond → get).
    8. Memory add / retrieve → hit count > 0.

This complements the 39 runtime probes by testing the *install surface*
as seen from outside the source tree.  Any regression that breaks user
onboarding will be caught here.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Scripts path — works from both repo-root layout (``tests/`` next to
# ``skill/``) and bundle layout (``tests/`` inside the skill).
_HERE = Path(__file__).resolve().parent
if (_HERE.parent / "skill" / "vibecodekit-hybrid-ultra").is_dir():
    # repo-root layout
    REPO_ROOT = _HERE.parent
    SKILL_ROOT = REPO_ROOT / "skill" / "vibecodekit-hybrid-ultra"
elif (_HERE.parent / "scripts" / "vibecodekit").is_dir():
    # bundled layout: tests/ inside skill/
    SKILL_ROOT = _HERE.parent
    REPO_ROOT = SKILL_ROOT
else:
    raise RuntimeError(
        f"cannot locate skill bundle from test file {__file__}; "
        f"expected either repo-root or bundled layout"
    )
SCRIPTS = SKILL_ROOT / "scripts"


def _run_cli(args, cwd, env=None):
    """Run ``python -m vibecodekit.cli <args>`` and return completed process."""
    e = os.environ.copy()
    e["PYTHONPATH"] = str(SCRIPTS)
    if env:
        e.update(env)
    return subprocess.run(
        [sys.executable, "-m", "vibecodekit.cli"] + list(args),
        cwd=str(cwd), env=e, capture_output=True, text=True, timeout=60,
    )


@pytest.fixture
def fresh_root(tmp_path):
    root = tmp_path / "user_project"
    root.mkdir()
    # Simulate a fresh user project
    (root / "README.md").write_text("# My App\n")
    return root


def _update_package_root() -> Path | None:
    """Locate the sibling update-package (layout documented in §5 of the
    v0.11.3 release notes).  Tries repo-root/.../update, then
    $VIBECODE_UPDATE_PACKAGE env var.
    """
    env_val = os.environ.get("VIBECODE_UPDATE_PACKAGE")
    if env_val:
        p = Path(env_val)
        if p.exists():
            return p
    # Repo-root layout: sibling ``update/`` or ``update-package/``.
    for cand in (REPO_ROOT / "update", REPO_ROOT.parent / "update",
                 REPO_ROOT / "update-package"):
        if cand.exists() and (cand / ".claude").exists():
            return cand
    return None


def test_audit_from_fresh_install(fresh_root):
    """User installs the kit and immediately runs /vibe-audit.

    Matches the documented install layout: extract update-package siblings
    first (``.claude/``, ``.claw/``, ``ai-rules/`` placeholders), then run
    ``vibe install`` which copies runtime assets under ``ai-rules/``.
    Audit must report 100 % parity end-to-end.
    """
    update_pkg = _update_package_root()
    if update_pkg is None:
        pytest.skip(
            "update-package not available for fresh-install audit "
            "(set $VIBECODE_UPDATE_PACKAGE or ship update/ alongside skill/)"
        )
    # 1. Mirror update-package contents into the fresh project.
    for entry in update_pkg.iterdir():
        dst = fresh_root / entry.name
        if entry.is_dir():
            shutil.copytree(entry, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(entry, dst)
    # 2. Run `vibe install` to populate ai-rules/vibecodekit/ with runtime assets.
    r_install = _run_cli(["install", str(fresh_root)], cwd=fresh_root)
    assert r_install.returncode == 0, r_install.stderr
    # 3. Now audit end-to-end at threshold 1.0 — expect 53/53.
    env = {"VIBECODE_UPDATE_PACKAGE": str(update_pkg)}
    r = _run_cli(["audit", "--threshold", "1.0"], cwd=fresh_root, env=env)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["parity"] == 1.0, out
    assert out["total"] == out["passed"], out
    assert out["total"] >= 53


def test_sample_plan_end_to_end(fresh_root):
    """User runs the bundled sample plan from their project dir."""
    # Bundled sample plan lives in runtime/ (checked-in for the audit).
    plan = SKILL_ROOT / "runtime" / "sample-plan.json"
    assert plan.exists(), "sample plan missing from bundle"
    r = _run_cli(["run", str(plan), "--mode", "default"], cwd=fresh_root)
    assert r.returncode == 0, r.stderr
    # Must terminate cleanly, not hang on user decision required.
    assert "plan_exhausted" in r.stdout or "plan_exhausted" in r.stderr


def test_permission_denies_dangerous(fresh_root):
    """Permission engine must block destructive rm even from installed root.

    ``vibe permission`` exits non-zero when the command is denied (signal
    for shell scripts); we read the JSON body regardless."""
    r = _run_cli(["permission", "rm -rf /"], cwd=fresh_root)
    # Exit code 2 = denied (signal to callers); we tolerate both 0 and 2
    # because of the circuit-breaker (``repeated denial within TTL``).
    assert r.returncode in (0, 2), (r.returncode, r.stderr)
    out = json.loads(r.stdout)
    assert out["decision"] == "deny"
    # Reason is either the original class or the circuit-breaker.
    assert any(kw in out["reason"].lower()
               for kw in ("destructive", "denial"))


def test_mcp_inproc_roundtrip(fresh_root):
    """Register bundled selfcheck MCP server in-process and call ping."""
    r1 = _run_cli(
        ["mcp", "register", "selfcheck",
         "--transport", "inproc",
         "--module", "vibecodekit.mcp_servers.selfcheck"],
        cwd=fresh_root,
    )
    assert r1.returncode == 0, r1.stderr
    r2 = _run_cli(["mcp", "call", "selfcheck", "ping"], cwd=fresh_root)
    assert r2.returncode == 0, r2.stderr
    out = json.loads(r2.stdout)
    # MCP call wraps tool output as {"ok": True, "result": {...}}
    # selfcheck.ping returns ``{"pong": True, "ts": ...}``.
    assert out.get("ok") is True
    assert out.get("result", {}).get("pong") is True


def test_approval_roundtrip(fresh_root):
    """Create approval → respond allow → get must show ``allow``."""
    r1 = _run_cli(
        ["approval", "create", "--title", "Deploy X",
         "--kind", "permission", "--risk", "high"],
        cwd=fresh_root,
    )
    assert r1.returncode == 0, r1.stderr
    created = json.loads(r1.stdout)
    aid = created["id"]

    r2 = _run_cli(
        ["approval", "respond", aid, "allow", "--note", "LGTM"],
        cwd=fresh_root,
    )
    assert r2.returncode == 0, r2.stderr

    r3 = _run_cli(["approval", "get", aid], cwd=fresh_root)
    assert r3.returncode == 0, r3.stderr
    got = json.loads(r3.stdout)
    # ``response.choice`` must reflect what we responded.
    assert got.get("response", {}).get("choice") == "allow"


def test_memory_add_retrieve(fresh_root):
    """Memory add → retrieve must surface the added content."""
    r1 = _run_cli(
        ["memory", "add", "project", "PostgreSQL 16 chosen over MySQL",
         "--header", "DB choice", "--source", "adr-0003.md"],
        cwd=fresh_root,
    )
    assert r1.returncode == 0, r1.stderr

    r2 = _run_cli(
        ["memory", "retrieve", "database", "--tiers", "project",
         "--top-k", "5"],
        cwd=fresh_root,
    )
    assert r2.returncode == 0, r2.stderr
    res = json.loads(r2.stdout)
    assert len(res.get("results", [])) >= 1


def test_vn_checklist_pass(fresh_root):
    """All 12 VN keys true → gate PASS."""
    flags = {
        "nfkd_diacritics": True, "address_cascade": True,
        "vnd_formatting": True, "cccd_12_digits": True,
        "date_dd_mm_yyyy": True, "phone_10_digits": True,
        "longest_string_layout": True, "diacritic_sort": True,
        "vn_money_spellout": True, "holidays_lunar": True,
        "encoding_utf8": True, "rtl_awareness": True,
    }
    r = _run_cli(
        ["vn-check", "--flags-json", json.dumps(flags)],
        cwd=fresh_root,
    )
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["gate"] == "PASS"
    assert out["summary"]["pass"] == 12


def test_dashboard_html_auto_creates_parent_dir(fresh_root, tmp_path):
    """v0.10.3.1 fix: dashboard --html should mkdir -p the parent dir."""
    target = tmp_path / "a" / "b" / "c" / "dash.html"
    assert not target.parent.exists()
    r = _run_cli(
        ["dashboard", "--root", str(fresh_root), "--html", str(target)],
        cwd=fresh_root,
    )
    assert r.returncode == 0, r.stderr
    assert target.exists()
    html = target.read_text(encoding="utf-8")
    assert "VibecodeKit" in html
    assert "<pre>" in html


def test_dashboard_html_permission_error_clean(fresh_root, tmp_path):
    """v0.10.3.1 fix: dashboard --html into an unwritable path yields a clean
    JSON error (no Python traceback).

    HOTFIX-006: use a directory-as-file target instead of /etc/nope.html so
    the test is deterministic under both unprivileged users and root
    containers where /etc is writable.
    """
    # A directory cannot be opened as a regular file for writing, so shutil
    # copyfile / open("w") both raise — this is portable across UIDs.
    blocker = tmp_path / "unwritable-as-file"
    blocker.mkdir()
    r = _run_cli(
        ["dashboard", "--root", str(fresh_root), "--html", str(blocker)],
        cwd=fresh_root,
    )
    # Non-zero but no Python traceback; JSON body explains.
    assert r.returncode == 1
    assert "Traceback" not in r.stderr
    body = json.loads(r.stdout)
    assert "error" in body
    detail = (body.get("detail") or "").lower()
    err = (body.get("error") or "").lower()
    assert (
        "permission" in detail
        or "cannot" in err
        or "directory" in detail
        or "isadirectoryerror" in err
        or "isadirectory" in err
    )


def test_embedding_backend_missing_raises(fresh_root):
    """v0.10.3.1 fix: explicit sbert request without dep must raise, not
    silently downgrade to hash-256."""
    import sys
    sys.path.insert(0, str(SCRIPTS))
    try:
        from vibecodekit.memory_hierarchy import get_backend
        # sentence-transformers is intentionally NOT a dependency of the
        # default install, so this should raise ValueError with a helpful
        # message (not silently return hash-256).
        try:
            backend = get_backend("sbert")
        except ValueError as e:
            assert "sentence-transformers" in str(e).lower() \
                or "sbert" in str(e).lower()
        except ImportError:
            # Acceptable — the lazy import may itself raise.
            pass
        else:
            # If we got here, sbert IS installed in this environment
            # (CI with sentence-transformers); that's fine — just assert
            # it's the right backend.
            assert backend.name == "sbert"

        # Unknown name must always raise
        try:
            get_backend("totally-made-up-backend")
            assert False, "should have raised"
        except ValueError:
            pass
    finally:
        sys.path.pop(0)


def test_stdio_session_public_request_api(fresh_root):
    """v0.10.3.1 feedback 8.2-7: ``StdioSession.request()`` public API."""
    import sys
    sys.path.insert(0, str(SCRIPTS))
    try:
        from vibecodekit.mcp_client import StdioSession
        # Verify public request/notify methods exist and have docstrings.
        assert hasattr(StdioSession, "request"), "StdioSession.request() missing"
        assert hasattr(StdioSession, "notify"), "StdioSession.notify() missing"
        assert StdioSession.request.__doc__ and len(StdioSession.request.__doc__) > 20
        # Verify public method is a thin wrapper (same call signature as _request).
        import inspect
        pub = inspect.signature(StdioSession.request)
        assert "method" in pub.parameters
        assert "params" in pub.parameters
    finally:
        sys.path.pop(0)


def test_platform_lock_helper_importable():
    """``_platform_lock`` helper must import on any platform (v0.10.3)."""
    # Add scripts to sys.path for the import test.
    import sys
    sys.path.insert(0, str(SCRIPTS))
    try:
        from vibecodekit._platform_lock import file_lock, has_real_locking
    finally:
        sys.path.pop(0)
    # Smoke-test the context manager actually yields.
    with tempfile.NamedTemporaryFile() as f:
        with file_lock(f.fileno()):
            pass  # entered + exited cleanly
    # On any POSIX or Windows dev machine this should be True; if it's
    # False we at least don't crash (degrades to NO-OP).
    assert isinstance(has_real_locking(), bool)
