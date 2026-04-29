"""Regression tests for the v0.16.0-α router-fix bundle (audit P2 #4 +
P2 #5 + P3 #9, ``docs/audits/v0.15.4-recheck.md``).

Each test pins a *behavioural* observation from the audit report so a
future refactor of the keyword banks can't silently re-open the bug.

Layout (4 sections):

1. ``vck-pipeline`` skill frontmatter declares triggers (P2 #4).
2. ``intent_router`` ``VCK_REVIEW`` / ``VCK_CSO`` / ``VCK_PIPELINE``
   bands beat ``SCAN`` on the audit's exact prose samples (P2 #5).
3. ``pipeline_router`` recognises the EN equivalents of the
   "go-through-the-whole-pipeline" phrases (P3 #9).
4. ``update-package/.claw/hooks/post_tool_use.py`` references the
   real ``auto_commit_hook`` module so the no-orphan probe (#85)
   sees a production call site (P2 #6 + P2 #7).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# 1.  vck-pipeline frontmatter triggers (P2 #4)
# ---------------------------------------------------------------------------

VCK_PIPELINE_SKILL = (
    REPO / "update-package" / ".claude" / "commands" / "vck-pipeline.md"
)


def _frontmatter(md_path: Path) -> str:
    text = md_path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return ""
    end = text.find("\n---", 4)
    return text[4:end] if end > 0 else ""


def test_vck_pipeline_frontmatter_has_triggers_block() -> None:
    fm = _frontmatter(VCK_PIPELINE_SKILL)
    assert "triggers:" in fm, (
        "vck-pipeline.md frontmatter must declare a `triggers:` block "
        "(audit P2 #4)"
    )


@pytest.mark.parametrize("phrase", [
    # Plan T6 mandated phrases.
    "pipeline",
    "đầy đủ",
    "day du",
    "full check",
    "go through pipeline",
    # Audit P3 #9 EN equivalents.
    "all gates",
    "end to end",
    "e2e check",
])
def test_vck_pipeline_frontmatter_lists_phrase(phrase: str) -> None:
    fm = _frontmatter(VCK_PIPELINE_SKILL)
    assert phrase in fm, (
        f"vck-pipeline.md triggers must include {phrase!r} (audit P2 #4 + #9)"
    )


# ---------------------------------------------------------------------------
# 2.  intent_router multi-token boost (P2 #5)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def router():
    sys.path.insert(0, str(REPO / "scripts"))
    from vibecodekit.intent_router import IntentRouter
    return IntentRouter()


def _intents_of(result) -> tuple[str, ...]:
    return getattr(result, "intents", ())


@pytest.mark.parametrize("prose,expected_intent", [
    # The exact phrase from the audit smoke that was mis-routing in v0.15.4.
    ("review my code for security", "VCK_REVIEW"),
    ("can you review my code for security", "VCK_REVIEW"),
    ("review my code", "VCK_REVIEW"),
    ("review the code", "VCK_REVIEW"),
    # Single-noun "code review" / "review code" must land on VCK_REVIEW
    # too (was mis-pinned to SCAN before v0.16.0-α).
    ("code review please", "VCK_REVIEW"),
    ("review code", "VCK_REVIEW"),
    # CSO bucket — security-audit verbs.
    ("audit my code for security", "VCK_CSO"),
    ("security audit pass", "VCK_CSO"),
    ("security review of api", "VCK_CSO"),
])
def test_intent_router_multi_token_boost(router, prose, expected_intent):
    res = router.classify(prose)
    intents = _intents_of(res)
    assert expected_intent in intents, (
        f"prose={prose!r} expected {expected_intent} in intents={intents} "
        f"(result={res})"
    )


@pytest.mark.parametrize("prose", [
    "pipeline đầy đủ",
    "pipeline day du",
    "go through pipeline",
    "full check",
    "all gates",
    "end to end",
    "e2e check",
])
def test_intent_router_pipeline_phrases_route_to_vck_pipeline(router, prose):
    res = router.classify(prose)
    intents = _intents_of(res)
    assert "VCK_PIPELINE" in intents, (
        f"prose={prose!r} must hit VCK_PIPELINE (got {intents}, result={res})"
    )


# ---------------------------------------------------------------------------
# 3.  pipeline_router EN equivalents (P3 #9)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pipeline_router():
    sys.path.insert(0, str(REPO / "scripts"))
    from vibecodekit import pipeline_router as pr
    return pr


@pytest.mark.parametrize("prose,expected_code", [
    ("build the whole thing", "A"),
    ("set everything up please", "A"),
    ("full check before merge", "B"),
    ("run all gates", "B"),
    ("end to end pass", "B"),
    ("e2e check", "B"),
    ("go through pipeline", "B"),
    ("pipeline đầy đủ trước khi ship", "B"),
    ("pipeline day du truoc khi ship", "B"),
])
def test_pipeline_router_recognises_en_equivalents(pipeline_router, prose, expected_code):
    decision = pipeline_router.PipelineRouter().route(prose)
    assert decision.pipeline == expected_code, (
        f"prose={prose!r} expected pipeline={expected_code} "
        f"got pipeline={decision.pipeline} confidence={decision.confidence}"
    )


# ---------------------------------------------------------------------------
# 4.  auto_commit_hook wired into post_tool_use.py (P2 #6 + P2 #7)
# ---------------------------------------------------------------------------

POST_TOOL_USE_HOOK = (
    REPO / "update-package" / ".claw" / "hooks" / "post_tool_use.py"
)


def test_post_tool_use_hook_imports_auto_commit_hook() -> None:
    text = POST_TOOL_USE_HOOK.read_text(encoding="utf-8")
    assert re.search(
        r"from\s+vibecodekit\.auto_commit_hook\s+import\s+AutoCommitHook",
        text,
    ), "post_tool_use.py must import AutoCommitHook (audit P2 #6 + #7)"


def test_post_tool_use_hook_returns_allow_envelope_by_default(tmp_path: Path) -> None:
    """Calling the hook with no env opt-in must NOT auto-commit but must
    still emit ``decision: allow`` so the runtime treats it as success."""
    env = os.environ.copy()
    env.pop("VIBECODE_AUTOCOMMIT", None)
    env["VIBECODE_HOOK_PAYLOAD"] = json.dumps({"tool": "Edit"})
    env["PYTHONPATH"] = (
        str(REPO / "scripts") + os.pathsep + env.get("PYTHONPATH", "")
    )
    proc = subprocess.run(
        [sys.executable, str(POST_TOOL_USE_HOOK)],
        capture_output=True, text=True, env=env, cwd=str(tmp_path), timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    parsed = json.loads(proc.stdout)
    assert parsed["decision"] == "allow"
    assert parsed["observed_tool"] == "Edit"
    assert parsed["auto_commit"]["ran"] is False
    assert "VIBECODE_AUTOCOMMIT" in parsed["auto_commit"]["reason"]


def test_post_tool_use_hook_runs_auto_commit_when_opted_in(tmp_path: Path) -> None:
    """With ``VIBECODE_AUTOCOMMIT=1`` set, the hook must drive
    ``AutoCommitHook.commit()`` against the project root.  We verify by
    running the hook against an *empty* git repo (no staged changes →
    decision is ``no-op`` not ``commit``)."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)

    env = os.environ.copy()
    env["VIBECODE_AUTOCOMMIT"] = "1"
    env["VIBECODE_PROJECT_ROOT"] = str(tmp_path)
    env["VIBECODE_HOOK_PAYLOAD"] = json.dumps({"tool": "Write"})
    env["PYTHONPATH"] = (
        str(REPO / "scripts") + os.pathsep + env.get("PYTHONPATH", "")
    )
    proc = subprocess.run(
        [sys.executable, str(POST_TOOL_USE_HOOK)],
        capture_output=True, text=True, env=env, cwd=str(tmp_path), timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    parsed = json.loads(proc.stdout)
    assert parsed["decision"] == "allow"
    auto = parsed["auto_commit"]
    assert auto["ran"] is True, parsed
    # Empty repo with no changes → AutoCommitHook returns commit=False with
    # a "no-op" reason; the hook envelope must surface that faithfully.
    assert auto["committed"] is False
    assert "no" in auto["reason"].lower() or "empty" in auto["reason"].lower()


def test_no_orphan_probe_sees_auto_commit_hook_via_post_tool_use_wiring() -> None:
    """The whole point of wiring ``auto_commit_hook`` into the hook was
    so that probe #85 can find it without an allowlist entry.  Verify
    the allowlist no longer mentions the module."""
    blob = json.loads(
        (REPO / "scripts" / "vibecodekit" / "_audit_allowlist.json").read_text(
            encoding="utf-8")
    )
    assert "auto_commit_hook" not in blob["no_orphan_module"], (
        "auto_commit_hook should NOT be allowlisted — its production "
        "call site is update-package/.claw/hooks/post_tool_use.py "
        "(audit P2 #6 + #7, decision option (a))."
    )
