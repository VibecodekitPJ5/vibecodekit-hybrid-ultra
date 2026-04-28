"""Sanity tests for the 7 gstack-inspired /vck-* slash commands.

These tests stay deliberately simple — they assert the *structural*
guarantees required by audit probes #63–#67 (presence + attribution +
agent binding + license) so a future edit cannot silently drop one.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
SCRIPTS = KIT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

COMMANDS = KIT / "update-package" / ".claude" / "commands"
AGENTS = KIT / "update-package" / ".claude" / "agents"

EXPECTED_COMMANDS = {
    "vck-cso", "vck-review", "vck-qa", "vck-qa-only",
    "vck-ship", "vck-investigate", "vck-canary",
}
EXPECTED_AGENTS = {"reviewer", "qa-lead"}


pytestmark = pytest.mark.skipif(
    not COMMANDS.is_dir(),
    reason="test requires update-package overlay on disk",
)


def test_all_vck_commands_ship() -> None:
    present = {p.stem for p in COMMANDS.glob("vck-*.md")}
    assert EXPECTED_COMMANDS.issubset(present), (
        f"missing /vck-* commands: {sorted(EXPECTED_COMMANDS - present)}"
    )


def test_each_vck_command_has_gstack_attribution() -> None:
    for name in EXPECTED_COMMANDS:
        body = (COMMANDS / f"{name}.md").read_text(encoding="utf-8")
        assert "inspired-by:" in body, f"{name}.md missing inspired-by frontmatter"
        assert "gstack" in body, f"{name}.md missing gstack reference"
        assert "LICENSE-third-party" in body or "MIT" in body, (
            f"{name}.md does not reference LICENSE-third-party.md or MIT"
        )


def test_new_agents_exist() -> None:
    for name in EXPECTED_AGENTS:
        p = AGENTS / f"{name}.md"
        assert p.is_file(), f"agent file missing: {p}"


def test_new_agents_registered_in_subagent_runtime() -> None:
    from vibecodekit import subagent_runtime as sr  # type: ignore
    for role in EXPECTED_AGENTS:
        assert role in sr.PROFILES, f"role {role!r} missing from PROFILES"
        assert sr.PROFILES[role].get("can_mutate", True) is False, (
            f"{role!r} must be read-only"
        )


def test_command_agent_bindings_present() -> None:
    from vibecodekit import subagent_runtime as sr  # type: ignore
    want = {
        "vck-review": "reviewer",
        "vck-cso": "security",
        "vck-qa": "qa-lead",
        "vck-qa-only": "qa-lead",
        "vck-investigate": "scout",
        "vck-canary": "qa",
        "vck-ship": "coordinator",
    }
    got = sr.list_command_agent_bindings()
    for cmd, role in want.items():
        assert got.get(cmd) == role, f"{cmd!r} → got {got.get(cmd)!r}, want {role!r}"


def test_manifest_lists_all_vck_commands() -> None:
    manifest = json.loads((KIT / "manifest.llm.json").read_text(encoding="utf-8"))
    names = {c["name"] for c in manifest["commands"]}
    assert EXPECTED_COMMANDS.issubset(names), (
        f"manifest.llm.json missing: {sorted(EXPECTED_COMMANDS - names)}"
    )
    triggers = set(manifest["skill_frontmatter"]["triggers"])
    for cmd in EXPECTED_COMMANDS:
        assert f"/{cmd}" in triggers, f"trigger /{cmd} missing from manifest.llm.json"


def test_manifest_lists_new_agents() -> None:
    manifest = json.loads((KIT / "manifest.llm.json").read_text(encoding="utf-8"))
    names = {a["name"] for a in manifest["agents"]}
    assert EXPECTED_AGENTS.issubset(names), (
        f"manifest.llm.json missing agents: {sorted(EXPECTED_AGENTS - names)}"
    )


def test_skill_md_lists_vck_triggers() -> None:
    body = (KIT / "SKILL.md").read_text(encoding="utf-8")
    for cmd in EXPECTED_COMMANDS:
        assert f"/{cmd}" in body, f"SKILL.md missing trigger /{cmd}"


def test_license_files_present() -> None:
    lic = KIT / "LICENSE"
    third = KIT / "LICENSE-third-party.md"
    assert lic.is_file(), "LICENSE missing"
    assert third.is_file(), "LICENSE-third-party.md missing"
    assert "MIT" in lic.read_text(encoding="utf-8")
    body3 = third.read_text(encoding="utf-8")
    assert "gstack" in body3 and "MIT" in body3


def test_ethos_reference_present() -> None:
    ethos = KIT / "references" / "40-ethos-vck.md"
    assert ethos.is_file(), "references/40-ethos-vck.md missing"
    body = ethos.read_text(encoding="utf-8")
    for principle in ("Boil the Lake", "Search Before Building",
                      "User Sovereignty", "Build for Yourself"):
        assert principle in body, f"ETHOS missing principle: {principle}"


def test_intent_router_routes_vck_ship_to_vck_ship() -> None:
    from vibecodekit import intent_router  # type: ignore
    r = intent_router.IntentRouter()
    for prose in ("/vck-ship", "atomic ship orchestrator please"):
        match = r.classify(prose)
        # IntentMatch always has .intents; Clarification does not.
        intents = getattr(match, "intents", ())
        assert "VCK_SHIP" in intents, f"{prose!r} did not route to VCK_SHIP: {intents}"


def test_intent_router_routes_vck_cso() -> None:
    from vibecodekit import intent_router  # type: ignore
    r = intent_router.IntentRouter()
    for prose in ("/vck-cso audit", "run OWASP Top 10 review"):
        match = r.classify(prose)
        intents = getattr(match, "intents", ())
        assert "VCK_CSO" in intents, f"{prose!r} did not route to VCK_CSO: {intents}"


def test_browser_package_importable_without_extras() -> None:
    """Core browser layer must import with stdlib only."""
    from vibecodekit.browser import (  # noqa: F401
        state, security, permission, snapshot,
        commands_read, commands_write, cli_adapter,
    )
    from vibecodekit.browser import PROTOCOL_VERSION
    assert PROTOCOL_VERSION  # non-empty


def test_pyproject_browser_extras_declared() -> None:
    toml_path = KIT / "pyproject.toml"
    assert toml_path.is_file(), "pyproject.toml missing"
    body = toml_path.read_text(encoding="utf-8")
    assert "playwright" in body
    assert "fastapi" in body
    assert "[project.optional-dependencies]" in body
