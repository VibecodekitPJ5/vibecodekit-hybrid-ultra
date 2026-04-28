"""Version sync regression test — v0.10.3.1.

The user reported (v0.10.2 feedback #4) that ``.claw.json`` shipped with
``"version": "0.9.0"`` while the rest of the kit was 0.10.2.  This test
enforces that every version string in the deliverables matches the
canonical ``VERSION`` file, so a future release cannot drift silently.

Files checked:

  VERSION                                      (canonical)
  skill/.../SKILL.md                           YAML front-matter
  skill/.../assets/plugin-manifest.json        "version" field
  claw-code-pack/.claw.json                    "version" field
  claw-code-pack/CLAUDE.md                     header
  skill/.../scripts/vibecodekit/mcp_client.py  initialize() default
  skill/.../scripts/vibecodekit/mcp_servers/selfcheck.py  serverInfo.version
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "skill" / "vibecodekit-hybrid-ultra"
PACK = REPO / "claw-code-pack"

# When this test is run from inside the bundled ``tests/`` folder (i.e.
# the skill zip extracted somewhere) the repo-root layout won't exist,
# so we skip at collection time with a clear message.
pytestmark = pytest.mark.skipif(
    not (SKILL.is_dir() and PACK.is_dir()),
    reason="version-sync test only runs from the repo-root layout; "
           "skipped when executed from inside the bundled skill zip.",
)


@pytest.fixture(scope="module")
def canonical_version() -> str:
    v = (REPO / "VERSION").read_text(encoding="utf-8").strip()
    assert re.fullmatch(r"\d+\.\d+\.\d+", v), f"bad VERSION: {v!r}"
    return v


def test_skill_md_version(canonical_version):
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    m = re.search(r"^version:\s*([0-9.]+)", text, re.MULTILINE)
    assert m, "no `version:` field in SKILL.md front-matter"
    assert m.group(1) == canonical_version, (m.group(1), canonical_version)


def test_plugin_manifest_version(canonical_version):
    data = json.loads((SKILL / "assets" / "plugin-manifest.json").read_text(encoding="utf-8"))
    assert data["version"] == canonical_version


def test_claw_json_version(canonical_version):
    data = json.loads((PACK / ".claw.json").read_text(encoding="utf-8"))
    assert data["version"] == canonical_version, (
        f"{data['version']!r} != {canonical_version!r} "
        f"(v0.10.2 feedback #4 regression)"
    )


def test_claude_md_version(canonical_version):
    text = (PACK / "CLAUDE.md").read_text(encoding="utf-8")
    # Header should mention the current version exactly once (modulo the
    # repeated "v0.10.3" in section copy — we require ≥ 1 occurrence).
    assert f"v{canonical_version}" in text, (
        f"v{canonical_version} not found in CLAUDE.md "
        f"(v0.10.2 feedback #5 regression)"
    )
    # Also assert that no stale old-major versions (v0.7 / v0.8 / v0.9) leak
    # through in user-facing sentences (they may legitimately appear in
    # historical notes / tables; we grep specifically for ``v0.7 overlay``
    # style marketing copy).
    assert "v0.7 overlay" not in text
    assert "v0.8 overlay" not in text
    assert "v0.9 overlay" not in text


def test_mcp_client_default(canonical_version):
    text = (SKILL / "scripts" / "vibecodekit" / "mcp_client.py").read_text(encoding="utf-8")
    m = re.search(r'client_version:\s*str\s*=\s*"([^"]+)"', text)
    assert m, "could not find client_version default"
    assert m.group(1) == canonical_version


def test_init_py_fallback_version(canonical_version):
    """``__init__.py`` contains a fallback string that must match VERSION."""
    text = (SKILL / "scripts" / "vibecodekit" / "__init__.py"
           ).read_text(encoding="utf-8")
    m = re.search(r'_FALLBACK_VERSION\s*=\s*"([^"]+)"', text)
    assert m, "could not find _FALLBACK_VERSION"
    assert m.group(1) == canonical_version, (
        f"{m.group(1)!r} != {canonical_version!r} "
        f"(v0.10.3.1 feedback 8.1-1 regression)"
    )


def test_init_py_runtime_version(canonical_version):
    """Import ``vibecodekit`` and verify runtime ``__version__``."""
    import sys
    p = str(SKILL / "scripts")
    if p not in sys.path:
        sys.path.insert(0, p)
    # Force re-import to pick up the current tree.
    sys.modules.pop("vibecodekit", None)
    import vibecodekit  # noqa: E402
    assert vibecodekit.__version__ == canonical_version
    assert vibecodekit.VERSION == canonical_version


def test_update_package_readme_version(canonical_version):
    text = (PACK / "README.md").read_text(encoding="utf-8")
    assert f"v{canonical_version}" in text, (
        f"v{canonical_version} not found in update-package/README.md "
        f"(v0.10.3.1 feedback 8.1-2 regression)"
    )
    # Zip name in install command should also match.
    assert f"v{canonical_version}-update-package" in text, (
        "install command in README still references stale zip name"
    )


def test_claude_md_release_gate_pytest_count(canonical_version):
    """Release gate in CLAUDE.md should not reference a stale test count."""
    text = (PACK / "CLAUDE.md").read_text(encoding="utf-8")
    assert "284/284" not in text, (
        "CLAUDE.md release gate still mentions v0.10.2 count 284/284 "
        "(v0.10.3.1 feedback 8.1-3 regression)"
    )


def test_bundled_version_file(canonical_version):
    """A ``VERSION`` file must ship inside the skill bundle."""
    bundled = SKILL / "VERSION"
    assert bundled.is_file(), f"missing bundled {bundled}"
    assert bundled.read_text(encoding="utf-8").strip() == canonical_version


def test_bundled_quickstart(canonical_version):
    """``QUICKSTART.md`` must ship inside the skill bundle (feedback 8.1-4)."""
    assert (SKILL / "QUICKSTART.md").is_file(), (
        "QUICKSTART.md not shipped inside skill bundle"
    )
    assert (PACK / "QUICKSTART.md").is_file(), (
        "QUICKSTART.md not shipped inside update-package"
    )


def test_bundled_integration_tests(canonical_version):
    """``test_end_to_end_install.py`` must ship inside the skill bundle
    (feedback 8.1-5) so a user can audit install behaviour themselves."""
    bundled = SKILL / "tests" / "test_end_to_end_install.py"
    assert bundled.is_file(), f"missing bundled {bundled}"


def test_bundled_usage_guide(canonical_version):
    """``USAGE_GUIDE.md`` must ship inside both bundles so users reading the
    zip on their laptop have the full 1000-line walkthrough, not just the
    5-minute QUICKSTART."""
    assert (SKILL / "USAGE_GUIDE.md").is_file(), (
        "USAGE_GUIDE.md not shipped inside skill bundle"
    )
    assert (PACK / "USAGE_GUIDE.md").is_file(), (
        "USAGE_GUIDE.md not shipped inside update-package"
    )


def test_usage_guide_version_match(canonical_version):
    """``USAGE_GUIDE.md`` must mention the current version in the header."""
    text = (REPO / "USAGE_GUIDE.md").read_text(encoding="utf-8")
    assert f"**v{canonical_version}**" in text, (
        f"USAGE_GUIDE.md does not mention current **v{canonical_version}** "
        f"(usage-guide version drift)"
    )
    # Stale version strings should NOT appear in the header / install section.
    # (They may legitimately appear in Phụ lục C semver history table.)
    header = text[:3000]  # first ~100 lines
    for stale in ("v0.10.2", "v0.10.1", "v0.10.0", "v0.9", "v0.7"):
        assert stale not in header, (
            f"stale version {stale!r} in USAGE_GUIDE.md header "
            f"(should only appear in semver history appendix)"
        )


def test_selfcheck_server_version(canonical_version):
    text = (SKILL / "scripts" / "vibecodekit" / "mcp_servers" / "selfcheck.py"
           ).read_text(encoding="utf-8")
    m = re.search(
        r'"serverInfo":\s*\{\s*"name":\s*"vibecodekit-selfcheck",\s*"version":\s*"([^"]+)"',
        text,
    )
    assert m, "could not find selfcheck serverInfo.version"
    assert m.group(1) == canonical_version
