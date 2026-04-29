"""v0.11.2 / FIX-007 — content-depth regression tests.

Cover the five gaps that TIP-FIX-001..005 close so they cannot reappear:

* docs scaffold + intent routing  (FIX-001)
* PROJECT_STACK_RECOMMENDATIONS + recommend_stack() safe fallback  (FIX-002)
* RRI question bank thresholds + persona/mode filter  (FIX-003)
* references/34-style-tokens.md VN typography rules  (FIX-004)
* references/36-copy-patterns.md + COPY_PATTERNS_VN  (FIX-005)

These tests run from a layout where ``tests/`` is a sibling of
``scripts/`` and ``references/`` (i.e. the kit's repo or the
extracted skill bundle).
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

# Skip the whole module if the kit layout isn't reachable (e.g. when only
# the tests/ folder is shipped on its own).
pytestmark = pytest.mark.skipif(
    not (SCRIPTS.is_dir() and (KIT / "references").is_dir()),
    reason="content-depth tests require the kit layout (scripts/ + references/)",
)


# ---------------------------------------------------------------------------
# FIX-001 — docs intent routing + scaffold
# ---------------------------------------------------------------------------

def test_intent_router_routes_docs_to_build():
    from vibecodekit import intent_router  # type: ignore
    r = intent_router.IntentRouter()
    cases = (
        "build docs site cho team kỹ thuật",
        "tạo trang tài liệu cho sản phẩm",
        "create developer documentation",
        "we need a knowledge base for the team",
    )
    for prose in cases:
        match = r.classify(prose)
        assert "BUILD" in match.intents, (prose, match.intents)


def test_docs_scaffold_preset_listed():
    from vibecodekit import scaffold_engine  # type: ignore
    engine = scaffold_engine.ScaffoldEngine()
    names = {p.name for p in engine.list_presets()}
    assert "docs" in names, f"docs preset missing from registry: {sorted(names)}"


def test_docs_scaffold_preview_files():
    from vibecodekit import scaffold_engine  # type: ignore
    engine = scaffold_engine.ScaffoldEngine()
    plan = engine.preview("docs", stack="nextjs",
                          target_dir=KIT / "tmp-docs-target")
    paths = {f.rel_path for f in plan.files}
    must_have = {
        "package.json",
        "next.config.mjs",
        "pages/index.mdx",
        "pages/_meta.json",
    }
    assert must_have.issubset(paths), sorted(must_have - paths)


# ---------------------------------------------------------------------------
# FIX-002 — recommend_stack
# ---------------------------------------------------------------------------

EXPECTED_STACK_TYPES = {
    "landing", "saas", "dashboard", "blog", "docs", "portfolio",
    "ecommerce", "mobile", "api", "enterprise-module", "custom",
}


def test_stack_recommendations_cover_all_types():
    from vibecodekit import methodology  # type: ignore
    have = set(methodology.PROJECT_STACK_RECOMMENDATIONS.keys())
    assert EXPECTED_STACK_TYPES.issubset(have), (
        sorted(EXPECTED_STACK_TYPES - have))


@pytest.mark.parametrize("project_type", sorted(EXPECTED_STACK_TYPES))
def test_recommend_stack_canonical(project_type):
    from vibecodekit import methodology  # type: ignore
    rec = methodology.recommend_stack(project_type)
    for key in ("framework", "styling", "state_data", "auth", "hosting", "extras"):
        assert key in rec, f"{project_type}: missing {key}"
    assert rec.get("unknown") in (False, None)
    assert rec.get("resolved_from") == project_type


@pytest.mark.parametrize("alias,expected", [
    ("landing-page", "landing"),
    ("documentation", "docs"),
    ("backend", "api"),
    ("module", "enterprise-module"),
    ("react-native", "mobile"),
])
def test_recommend_stack_aliases(alias, expected):
    from vibecodekit import methodology  # type: ignore
    rec = methodology.recommend_stack(alias)
    assert rec.get("unknown") in (False, None)
    canon = methodology.recommend_stack(expected)
    assert rec["framework"] == canon["framework"]


def test_recommend_stack_unknown_falls_back():
    from vibecodekit import methodology  # type: ignore
    rec = methodology.recommend_stack("super-niche-blockchain-thing")
    assert rec.get("unknown") is True
    # Must still return all required keys (safe default = custom row).
    for key in ("framework", "styling", "state_data", "auth", "hosting", "extras"):
        assert key in rec


@pytest.mark.parametrize("empty_input", ["", None])
def test_recommend_stack_empty_is_unknown(empty_input):
    """B2 deep-dive: empty/None inputs must be flagged ``unknown=True`` for
    consistency with other unrecognised inputs."""
    from vibecodekit import methodology  # type: ignore
    rec = methodology.recommend_stack(empty_input or "")
    assert rec.get("unknown") is True
    assert rec["framework"] == methodology.PROJECT_STACK_RECOMMENDATIONS["custom"]["framework"]


# ---------------------------------------------------------------------------
# FIX-003 — RRI question bank
# ---------------------------------------------------------------------------

THRESHOLDS = {
    "landing": 25, "saas": 50, "dashboard": 35, "blog": 25, "docs": 30,
    "portfolio": 25, "ecommerce": 40, "enterprise-module": 45, "custom": 15,
}


def test_question_bank_meets_all_thresholds():
    bank = json.loads(
        (KIT / "assets" / "rri-question-bank.json").read_text(encoding="utf-8"))
    types = bank["project_types"]
    for project, minimum in THRESHOLDS.items():
        assert project in types, f"missing project type {project}"
        actual = len(types[project]["questions"])
        assert actual >= minimum, (
            f"{project}: {actual} q < {minimum} threshold")


def test_question_bank_has_all_personas_and_modes():
    from vibecodekit import methodology  # type: ignore
    valid_personas = set(methodology.VALID_RRI_PERSONAS)
    valid_modes = set(methodology.VALID_RRI_MODES)
    bank = json.loads(
        (KIT / "assets" / "rri-question-bank.json").read_text(encoding="utf-8"))
    for project, payload in bank["project_types"].items():
        questions = payload["questions"]
        personas = {q["persona"] for q in questions}
        modes = {q["mode"] for q in questions}
        assert personas <= valid_personas, (project, personas - valid_personas)
        assert modes <= valid_modes, (project, modes - valid_modes)
        # Every persona must appear at least once for non-custom types.
        if project != "custom":
            assert personas == valid_personas, (project, valid_personas - personas)
            assert modes == valid_modes, (project, valid_modes - modes)


def test_load_rri_questions_filters():
    from vibecodekit import methodology  # type: ignore
    all_saas = methodology.load_rri_questions("saas")
    saas_dev = methodology.load_rri_questions("saas", persona="developer")
    saas_dev_guided = methodology.load_rri_questions(
        "saas", persona="developer", mode="GUIDED")
    assert len(all_saas) >= 50
    assert 0 < len(saas_dev) < len(all_saas)
    assert 0 < len(saas_dev_guided) <= len(saas_dev)
    for q in saas_dev_guided:
        assert q["persona"] == "developer" and q["mode"] == "GUIDED"


def test_load_rri_questions_unknown_falls_back_to_custom():
    from vibecodekit import methodology  # type: ignore
    qs = methodology.load_rri_questions("totally-fake-type")
    custom = methodology.load_rri_questions("custom")
    assert len(qs) == len(custom)


def test_load_rri_questions_validates_persona_and_mode():
    from vibecodekit import methodology  # type: ignore
    with pytest.raises(ValueError):
        methodology.load_rri_questions("saas", persona="invalid")
    with pytest.raises(ValueError):
        methodology.load_rri_questions("saas", mode="invalid")


# ---------------------------------------------------------------------------
# FIX-004 — VN typography rules
# ---------------------------------------------------------------------------

def test_style_tokens_has_vn_typography_rules():
    text = (KIT / "references" / "34-style-tokens.md").read_text(encoding="utf-8")
    for n in range(1, 13):
        tag = f"VN-{n:02d}"
        assert tag in text, f"34-style-tokens.md missing rule {tag}"


def test_methodology_font_pairings_and_color_psychology_intact():
    from vibecodekit import methodology  # type: ignore
    assert len(methodology.FONT_PAIRINGS) == 6
    assert len(methodology.COLOR_PSYCHOLOGY) == 6
    for n in range(1, 7):
        assert f"FP-0{n}" in methodology.FONT_PAIRINGS
        assert f"CP-0{n}" in methodology.COLOR_PSYCHOLOGY


# ---------------------------------------------------------------------------
# FIX-005 — copy patterns
# ---------------------------------------------------------------------------

def test_copy_patterns_reference_exists_and_is_complete():
    text = (KIT / "references" / "36-copy-patterns.md").read_text(encoding="utf-8")
    for n in range(1, 10):
        assert f"CF-{n:02d}" in text
    for n in range(1, 9):
        assert f"CF-VN-{n:02d}" in text


def test_methodology_copy_patterns_in_sync():
    from vibecodekit import methodology  # type: ignore
    assert len(methodology.COPY_PATTERNS) == 9
    assert len(methodology.COPY_PATTERNS_VN) == 8
    # Look-up still works for new IDs.
    assert methodology.lookup_style_token("CF-07") is not None
    assert methodology.lookup_style_token("CF-09") is not None


# ---------------------------------------------------------------------------
# B1 (deep-dive) — install_manifest must ship runtime data assets
# ---------------------------------------------------------------------------

def test_install_manifest_ships_runtime_data():
    from vibecodekit import install_manifest  # type: ignore
    plan = install_manifest.plan("/tmp/v0112_install_check")
    dests = [p.destination for p in plan]
    assert any("assets/rri-question-bank.json" in d for d in dests), (
        "install_manifest must ship rri-question-bank.json so "
        "load_rri_questions() works in installed projects")
    assert any("assets/scaffolds/docs/manifest.json" in d for d in dests), (
        "install_manifest must ship docs scaffold so scaffold_engine "
        "finds it in installed projects")
    # All 9 scaffold presets ship.
    for preset in ("landing-page", "saas", "portfolio", "docs",
                   "blog", "dashboard", "shop-online", "mobile-app",
                   "api-todo", "crm"):
        assert any(f"assets/scaffolds/{preset}/" in d for d in dests), (
            f"install_manifest missing scaffold preset: {preset}")


# ---------------------------------------------------------------------------
# v0.11.3 / Patch A — references → prompts wiring
# ---------------------------------------------------------------------------
import pytest


def test_load_reference_returns_body():
    from vibecodekit import methodology  # type: ignore
    body = methodology.load_reference("ref-34")
    assert "FP-01" in body
    assert "VN-01" in body  # Vietnamese typography section


def test_load_reference_alt_id_forms():
    from vibecodekit import methodology  # type: ignore
    a = methodology.load_reference("ref-30")
    b = methodology.load_reference("30")
    assert a == b


def test_load_reference_section_extracts():
    from vibecodekit import methodology  # type: ignore
    sec = methodology.load_reference_section(
        "ref-34",
        "3. Vietnamese-first typography & layout rules (VN-01..VN-12)",
    )
    assert "VN-01" in sec
    assert "VN-12" in sec


@pytest.mark.parametrize(
    "command,expected_refs",
    [
        ("vibe-vision",    ["ref-30", "ref-34"]),
        ("vibe-rri",       ["ref-21", "ref-29"]),
        ("vibe-rri-ui",    ["ref-22", "ref-33", "ref-34"]),
        ("vibe-rri-ux",    ["ref-22", "ref-32"]),
        ("vibe-blueprint", ["ref-30"]),
        ("vibe-verify",    ["ref-25", "ref-26"]),
        ("vibe-refine",    ["ref-30", "ref-36"]),
        ("vibe-audit",     ["ref-25", "ref-26", "ref-32"]),
        ("vibe-module",    ["ref-35"]),
    ],
)
def test_render_command_context_emits_refs(command, expected_refs):
    from vibecodekit import methodology  # type: ignore
    ctx = methodology.render_command_context(command)
    for r in expected_refs:
        assert r in ctx, f"{command} missing {r}"


def test_render_command_context_pulls_recommend_stack():
    from vibecodekit import methodology  # type: ignore
    ctx = methodology.render_command_context("vibe-vision", project_type="dashboard")
    assert "Dynamic: stack recommendation" in ctx
    assert "framework: Next.js" in ctx
    assert "resolved_from: dashboard" in ctx


def test_render_command_context_pulls_rri_questions():
    from vibecodekit import methodology  # type: ignore
    ctx = methodology.render_command_context(
        "vibe-rri", project_type="saas", persona="qa", mode="CHALLENGE", max_questions=5,
    )
    assert "Dynamic: RRI question subset" in ctx
    # IDs use S- (saas) -QA- (qa) -CH (challenge) shape
    assert "S-QA-CH" in ctx


def test_render_command_context_unknown_returns_empty():
    from vibecodekit import methodology  # type: ignore
    assert methodology.render_command_context("vibe-nonsense") == ""


# ---------------------------------------------------------------------------
# v0.11.3 / Patch B — agent auto-spawn binding
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "command,expected_role",
    [
        ("vibe-blueprint", "coordinator"),
        ("vibe-scaffold",  "builder"),
        ("vibe-module",    "builder"),
        ("vibe-verify",    "qa"),
        ("vibe-audit",     "security"),
        ("vibe-scan",      "scout"),
    ],
)
def test_default_command_agent_binding(command, expected_role):
    from vibecodekit import subagent_runtime  # type: ignore
    assert subagent_runtime.list_command_agent_bindings()[command] == expected_role


def test_command_frontmatter_overrides_default(tmp_path):
    from vibecodekit import subagent_runtime  # type: ignore
    cdir = tmp_path / "cmds"
    cdir.mkdir()
    (cdir / "vibe-verify.md").write_text(
        "---\nname: vibe-verify\nagent: scout\n---\n\nbody\n", encoding="utf-8"
    )
    assert subagent_runtime.resolve_command_agent("vibe-verify", commands_dir=cdir) == "scout"
    # No frontmatter file → falls back to default.
    assert subagent_runtime.resolve_command_agent("vibe-blueprint", commands_dir=cdir) == "coordinator"


def test_spawn_for_command_creates_agent(tmp_path):
    from vibecodekit import subagent_runtime  # type: ignore
    state = subagent_runtime.spawn_for_command(tmp_path, "vibe-blueprint", "plan things")
    assert state["role"] == "coordinator"
    assert state["objective"] == "plan things"
    assert (tmp_path / ".vibecode" / "runtime" / "agents" / state["agent_id"] / "state.json").exists()


def test_spawn_for_command_unknown_raises(tmp_path):
    from vibecodekit import subagent_runtime  # type: ignore
    with pytest.raises(LookupError):
        subagent_runtime.spawn_for_command(tmp_path, "vibe-nonexistent", "x")


# ---------------------------------------------------------------------------
# v0.11.3 / Patch C — paths-based skill activation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "path,expected",
    [
        # VibecodeKit overlay files — should activate
        (".vibecode/memory/project.json", True),
        (".claw/hooks/pre_tool_use.py", True),
        (".claw.json", True),
        ("SKILL.md", True),
        ("CLAUDE.md", True),
        ("manifest.llm.json", True),
        ("ai-rules/vibecodekit/references/10-permission.md", True),
        ("scripts/vibecodekit/cli.py", True),
        ("assets/scaffolds/api-todo/manifest.json", True),
        ("pyproject.toml", True),
        (".claude/commands/vibe-scan.md", True),
        (".claude/agents/coordinator.md", True),
        ("references/07-coordinator-restriction.md", True),
        ("tools/sync_version.py", True),
        # User's own code — should NOT activate
        ("src/main.py", False),
        ("a/b/c/Component.tsx", False),
        ("services/auth/handler.go", False),
        ("logo.png", False),
        ("image.svg", False),
        ("", False),
    ],
)
def test_skill_activation_by_path(path, expected):
    from vibecodekit import skill_discovery  # type: ignore
    out = skill_discovery.activate_for(path)
    assert out["activate"] is expected, f"path={path!r} reason={out.get('reason')}"


def test_skill_activation_reports_matched_glob():
    from vibecodekit import skill_discovery  # type: ignore
    out = skill_discovery.activate_for("scripts/vibecodekit/cli.py")
    assert out["activate"] is True
    assert "**/scripts/vibecodekit/**" in out["matched"]
