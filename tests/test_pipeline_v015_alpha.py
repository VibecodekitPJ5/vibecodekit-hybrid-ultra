"""Pipeline-integration tests for v0.15.0-alpha (T1 + T2 + T8).

These tests pin the wire-up between dormant modules and the runtime —
exactly the dormancy that probe #78 will guard once T7 ships.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SHIP = REPO / "update-package" / ".claude" / "commands" / "vck-ship.md"
REVIEW = REPO / "update-package" / ".claude" / "commands" / "vck-review.md"
QA_ONLY = REPO / "update-package" / ".claude" / "commands" / "vck-qa-only.md"
LEARN = REPO / "update-package" / ".claude" / "commands" / "vck-learn.md"
CI = REPO / ".github" / "workflows" / "ci.yml"
TOUCHMAP = REPO / "tests" / "touchfiles.json"


# ---------------------------------------------------------------------------
# T1 — vck-ship Bước 0 wires team_mode
# ---------------------------------------------------------------------------

def test_vck_ship_invokes_team_mode_check():
    body = SHIP.read_text(encoding="utf-8")
    assert "Bước 0" in body, "/vck-ship must declare a Bước 0 (team-mode preflight)"
    assert "python -m vibecodekit.team_mode check" in body
    # Bước 0 must come before Bước 1 in the source.
    assert body.index("Bước 0") < body.index("Bước 1")


def test_vck_ship_clears_ledger_after_pr():
    body = SHIP.read_text(encoding="utf-8")
    assert "team_mode clear" in body
    # Clear must come AFTER the PR step.
    assert body.index("team_mode clear") > body.index("Bước 6")


def test_vck_review_records_gate():
    body = REVIEW.read_text(encoding="utf-8")
    assert "team_mode record --gate /vck-review" in body


def test_vck_qa_only_records_gate():
    body = QA_ONLY.read_text(encoding="utf-8")
    assert "team_mode record --gate /vck-qa-only" in body


def test_vck_learn_records_gate():
    body = LEARN.read_text(encoding="utf-8")
    assert "team_mode record --gate /vck-learn" in body


# ---------------------------------------------------------------------------
# T2 — vck-ship Bước 2 wires eval_select + CI preview job
# ---------------------------------------------------------------------------

def test_vck_ship_invokes_eval_select_when_map_exists():
    body = SHIP.read_text(encoding="utf-8")
    assert "tests/touchfiles.json" in body
    assert "vibecodekit.eval_select" in body
    # Must fall back to full suite when no map.
    assert "pytest tests" in body


def test_ci_runs_eval_select_preview_on_pr_and_push():
    body = CI.read_text(encoding="utf-8")
    assert "eval_select" in body
    # Both PR and push events covered (the on: clause).  Order-agnostic.
    assert re.search(r"^on:\s*\n(?:[ \t]+.*\n)*[ \t]+pull_request:", body, re.M), \
        "ci.yml must trigger on pull_request"
    assert re.search(r"^on:\s*\n(?:[ \t]+.*\n)*[ \t]+push:", body, re.M), \
        "ci.yml must trigger on push"
    # eval_select preview step references the touchfiles map.
    assert "tests/touchfiles.json" in body
    # fetch-depth: 0 so merge-base works for PRs.
    assert "fetch-depth: 0" in body


# ---------------------------------------------------------------------------
# touchfiles.json sanity
# ---------------------------------------------------------------------------

def test_touchfiles_json_loads_and_covers_real_tests():
    raw = json.loads(TOUCHMAP.read_text(encoding="utf-8"))
    # Every key is an existing test file.
    for k in raw:
        assert (REPO / k).is_file(), f"touchfile map references missing test: {k}"
    # Always-run entries are well-formed.
    for k, v in raw.items():
        if isinstance(v, dict):
            assert "files" in v
            assert "always_run" in v


def test_touchfiles_json_parseable_by_eval_select():
    """Exercise the real load_map / select_tests path."""
    import sys
    sys.path.insert(0, str(REPO / "scripts"))
    from vibecodekit.eval_select import load_map, select_tests
    tmap = load_map(TOUCHMAP)
    assert len(tmap) >= 10
    # Pretend we changed eval_select itself.
    res = select_tests(["scripts/vibecodekit/eval_select.py"], tmap)
    assert "tests/test_eval_select.py" in res.selected
    # Always-run tests are unconditionally selected.
    res2 = select_tests(["docs/UNRELATED.md"], tmap)
    assert "tests/test_docs_count_sync.py" in res2.always_run


# ---------------------------------------------------------------------------
# T8 — docs match reality (no aspirational lies)
# ---------------------------------------------------------------------------

def test_usage_guide_section_18_present_and_accurate():
    body = (REPO / "USAGE_GUIDE.md").read_text(encoding="utf-8")
    assert "§18. Activation Cheat Sheet" in body
    # The section must mention the v0.15.0-alpha truth — team_mode IS now
    # wired into /vck-ship Bước 0 (no longer aspirational).
    assert "Bước 0" in body
    assert "session_ledger" in body
    # eval_select must be listed as wired (post-T2).
    assert "/vck-ship` Bước 2" in body
    # 15 (not 8) total /vck-* commands as of v0.14.0.
    assert "15 `/vck-*`" in body


def test_readme_cheat_sheet_present():
    body = (REPO / "README.md").read_text(encoding="utf-8")
    assert "Activation cheat sheet" in body
    assert "team_mode" in body
    assert "eval_select" in body
    assert "USAGE_GUIDE.md#18-activation-cheat-sheet" in body
