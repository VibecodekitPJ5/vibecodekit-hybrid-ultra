"""Regression tests for v0.15.0-alpha PR-C (T5 + T6).

T5 — ``ScaffoldEngine.apply()`` seeds ``.vibecode/`` runtime files.
T6 — ``PipelineRouter`` dispatches prose into one of 3 pipelines.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))

from vibecodekit import scaffold_engine as se
from vibecodekit.pipeline_router import (
    PIPELINES,
    PipelineDecision,
    PipelineRouter,
)


# ---------------------------------------------------------------------------
# T5 — .vibecode/ seed
# ---------------------------------------------------------------------------

def test_seed_vibecode_creates_four_placeholder_files(tmp_path: Path) -> None:
    seeded = se.seed_vibecode_dir(tmp_path)
    assert sorted(seeded) == sorted([
        ".vibecode/learnings.jsonl",
        ".vibecode/team.json.example",
        ".vibecode/classifier.env.example",
        ".vibecode/README.md",
    ])
    for rel in seeded:
        assert (tmp_path / rel).is_file(), f"missing {rel}"


def test_seed_vibecode_is_idempotent(tmp_path: Path) -> None:
    """Re-running seed must NOT overwrite existing files."""
    first = se.seed_vibecode_dir(tmp_path)
    assert len(first) == 4

    # Mutate one file so we can detect overwrite.
    target = tmp_path / ".vibecode" / "learnings.jsonl"
    target.write_text("USER_DATA_DO_NOT_OVERWRITE\n", encoding="utf-8")

    second = se.seed_vibecode_dir(tmp_path)
    assert second == ()  # nothing newly created
    assert target.read_text(encoding="utf-8") == "USER_DATA_DO_NOT_OVERWRITE\n"


def test_seed_vibecode_team_example_is_valid_json(tmp_path: Path) -> None:
    se.seed_vibecode_dir(tmp_path)
    raw = (tmp_path / ".vibecode" / "team.json.example").read_text(
        encoding="utf-8"
    )
    parsed = json.loads(raw)
    assert "required_gates" in parsed
    assert isinstance(parsed["required_gates"], list)


def test_seed_vibecode_classifier_env_documents_opt_out(tmp_path: Path) -> None:
    se.seed_vibecode_dir(tmp_path)
    raw = (tmp_path / ".vibecode" / "classifier.env.example").read_text(
        encoding="utf-8"
    )
    # Must mention both opt-out vars introduced in PR-B.
    assert "VIBECODE_SECURITY_CLASSIFIER" in raw
    assert "VIBECODE_LEARNINGS_INJECT" in raw


def test_scaffold_apply_seeds_vibecode_dir(tmp_path: Path) -> None:
    """End-to-end: scaffold a real preset and assert .vibecode/ shows up."""
    target = tmp_path / "my-blog"
    engine = se.ScaffoldEngine()
    result = engine.apply("blog", target, stack="nextjs")
    assert result.vibecode_seeded, (
        f"scaffold didn't seed .vibecode/: {result}"
    )
    for rel in result.vibecode_seeded:
        assert (target / rel).is_file(), f"missing {rel}"


def test_scaffold_apply_can_skip_vibecode_seed(tmp_path: Path) -> None:
    target = tmp_path / "my-blog"
    engine = se.ScaffoldEngine()
    result = engine.apply("blog", target, stack="nextjs",
                          seed_vibecode=False)
    assert result.vibecode_seeded == ()
    assert not (target / ".vibecode").exists()


# ---------------------------------------------------------------------------
# T6 — PipelineRouter
# ---------------------------------------------------------------------------

def test_pipelines_have_three_buckets() -> None:
    codes = [p.code for p in PIPELINES]
    assert codes == ["A", "B", "C"]


def test_pipeline_a_routes_project_creation() -> None:
    r = PipelineRouter()
    d = r.route("làm cho tôi shop online bán cà phê")
    assert d.pipeline == "A"
    assert d.commands == ("/vibe-scaffold", "/vibe-blueprint")
    assert d.confidence >= 0.5
    assert not d.needs_clarification


def test_pipeline_b_routes_feature_dev() -> None:
    r = PipelineRouter()
    d = r.route("thêm tính năng login mới")
    assert d.pipeline == "B"
    assert d.commands == ("/vibe-run", "/vck-ship")


def test_pipeline_c_routes_code_security() -> None:
    r = PipelineRouter()
    d = r.route("audit code OWASP security review")
    assert d.pipeline == "C"
    assert d.commands == ("/vck-cso", "/vck-review")


def test_pipeline_router_handles_english() -> None:
    r = PipelineRouter()
    assert r.route("scaffold a new project").pipeline == "A"
    assert r.route("add feature to existing app").pipeline == "B"
    assert r.route("security audit harden owasp").pipeline == "C"


def test_pipeline_router_low_confidence_asks_clarification() -> None:
    r = PipelineRouter()
    d = r.route("xyzzy quux")
    assert d.pipeline is None
    assert d.needs_clarification is True
    assert d.confidence < 0.5
    assert "low confidence" in d.explain


def test_pipeline_router_empty_input() -> None:
    r = PipelineRouter()
    d = r.route("")
    assert d.pipeline is None
    assert d.needs_clarification is True
    assert d.confidence == 0.0


def test_pipeline_router_decision_serializable() -> None:
    """`as_dict()` round-trips through JSON without losing fields."""
    r = PipelineRouter()
    d = r.route("scaffold landing page")
    blob = json.dumps(d.as_dict(), ensure_ascii=False)
    parsed = json.loads(blob)
    assert parsed["pipeline"] == "A"
    assert parsed["commands"] == list(d.commands)
    assert isinstance(parsed["confidence"], float)


def test_pipeline_router_keywords_unique_per_pipeline() -> None:
    """Each keyword must belong to at most one pipeline so the router
    cannot accidentally fire two buckets equally."""
    seen: dict[str, str] = {}
    for p in PIPELINES:
        for kw in p.keywords:
            assert kw not in seen, (
                f"keyword {kw!r} appears in both {seen[kw]} and {p.code}"
            )
            seen[kw] = p.code


def test_pipeline_router_cli_route(capsys, monkeypatch) -> None:
    from vibecodekit import pipeline_router as pr
    rc = pr._main(["route", "audit code security"])
    assert rc == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["pipeline"] == "C"


def test_pipeline_router_cli_list(capsys) -> None:
    from vibecodekit import pipeline_router as pr
    rc = pr._main(["list"])
    assert rc == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert len(parsed) == 3
    assert {p["code"] for p in parsed} == {"A", "B", "C"}


# ---------------------------------------------------------------------------
# Manifest + intent_router wiring
# ---------------------------------------------------------------------------

def test_vck_pipeline_wired_in_manifest() -> None:
    raw = (REPO / "manifest.llm.json").read_text(encoding="utf-8")
    blob = json.loads(raw)
    triggers = blob["skill_frontmatter"]["triggers"]
    assert "/vck-pipeline" in triggers
    files = {entry["name"] for entry in blob["commands"]}
    assert "vck-pipeline" in files


def test_vck_pipeline_wired_in_intent_router() -> None:
    from vibecodekit.intent_router import _INTENT_TO_SLASH, TIER_1
    assert _INTENT_TO_SLASH.get("VCK_PIPELINE") == "/vck-pipeline"
    triggers = {name: kws for name, kws in TIER_1}
    assert "VCK_PIPELINE" in triggers
    assert "/vck-pipeline" in triggers["VCK_PIPELINE"]
