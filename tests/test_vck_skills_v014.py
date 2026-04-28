"""Sanity tests for the v0.14.0 plan-review + polish skills."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
COMMANDS_DIR = REPO_ROOT / "update-package" / ".claude" / "commands"

V014_COMMANDS = (
    "vck-office-hours",
    "vck-ceo-review",
    "vck-eng-review",
    "vck-design-consultation",
    "vck-design-review",
    "vck-learn",
    "vck-retro",
    "vck-second-opinion",
)


@pytest.mark.parametrize("name", V014_COMMANDS)
def test_command_markdown_ships(name: str):
    p = COMMANDS_DIR / f"{name}.md"
    assert p.is_file(), f"missing {p}"
    body = p.read_text(encoding="utf-8")
    # Frontmatter sanity.
    assert body.startswith("---\n"), f"{name} missing frontmatter"
    assert f"name: {name}" in body
    assert "inspired-by: gstack/" in body
    assert "license: MIT (adapted)" in body


def test_manifest_lists_all_v014_commands():
    manifest = json.loads((REPO_ROOT / "manifest.llm.json").read_text(encoding="utf-8"))
    names = {c["name"] for c in manifest["commands"]}
    for n in V014_COMMANDS:
        assert n in names, f"manifest.llm.json missing command {n}"
    triggers = set(manifest["skill_frontmatter"]["triggers"])
    for n in V014_COMMANDS:
        assert f"/{n}" in triggers, f"SKILL triggers missing /{n}"


def test_skill_md_lists_all_v014_triggers():
    body = (REPO_ROOT / "SKILL.md").read_text(encoding="utf-8")
    for n in V014_COMMANDS:
        assert f"/{n}" in body, f"SKILL.md missing /{n}"


def test_intent_router_routes_all_v014_intents():
    from vibecodekit import intent_router
    want = {
        "VCK_OFFICE_HOURS": "/vck-office-hours",
        "VCK_CEO_REVIEW": "/vck-ceo-review",
        "VCK_ENG_REVIEW": "/vck-eng-review",
        "VCK_DESIGN_CONSULTATION": "/vck-design-consultation",
        "VCK_DESIGN_REVIEW": "/vck-design-review",
        "VCK_LEARN": "/vck-learn",
        "VCK_RETRO": "/vck-retro",
        "VCK_SECOND_OPINION": "/vck-second-opinion",
    }
    for intent, slash in want.items():
        assert intent_router._INTENT_TO_SLASH[intent] == slash


def test_subagent_runtime_binds_all_v014_commands():
    from vibecodekit import subagent_runtime
    binds = subagent_runtime.list_command_agent_bindings()
    for n in V014_COMMANDS:
        assert n in binds, f"no agent bound to {n}"
        role = binds[n]
        assert role in subagent_runtime.PROFILES, f"{n} -> unknown role {role}"


def test_usage_guide_has_browser_section_17():
    body = (REPO_ROOT / "USAGE_GUIDE.md").read_text(encoding="utf-8")
    assert "§17" in body
    assert "browser" in body.lower()


def test_contributing_md_present_and_mentions_audit():
    p = REPO_ROOT / "CONTRIBUTING.md"
    assert p.is_file()
    body = p.read_text(encoding="utf-8")
    assert "conformance_audit" in body
    assert "MIT" in body


def test_ci_workflow_present_and_gates_audit():
    p = REPO_ROOT / ".github" / "workflows" / "ci.yml"
    assert p.is_file()
    body = p.read_text(encoding="utf-8")
    assert "pytest" in body
    assert "conformance_audit" in body


def test_pyproject_declares_ml_extra():
    body = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "[project.optional-dependencies]" in body
    assert "ml" in body
