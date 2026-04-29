"""HOTFIX-005 / REFINE-002: guard current-release docs against stale
version + count drift.

The substrings below described v0.10.x / v0.11.0 / v0.11.2 state (24 /
39 / 44 / 47 / 50 probes, 526 tests, 284 passed, 7 preset × 3 stacks,
etc.).  They must not appear anywhere in the *current-release* user-
facing docs except in explicitly-historical sections (per-version
headings, changelog tables, CHANGELOG.md body).

Scans:
- Skill bundle: ``SKILL.md``, ``QUICKSTART.md``, ``USAGE_GUIDE.md``,
  ``README.md`` (if present).
- Update package (auto-detected via ``$VIBECODE_UPDATE_PACKAGE`` or a
  sibling ``update``/``update-package`` dir next to the skill bundle):
  ``README.md``, ``QUICKSTART.md``, ``USAGE_GUIDE.md``, ``CLAUDE.md``.

CHANGELOG.md is intentionally **not** scanned — historical entries
there are load-bearing.
"""
from __future__ import annotations

import os
from pathlib import Path
import re

import pytest


SKILL_ROOT = Path(__file__).resolve().parents[1]


def _candidate_update_roots() -> list:
    """Precedence:
    1. ``$VIBECODE_UPDATE_PACKAGE`` (authoritative — used by CI).
    2. First sibling ``update`` or ``update-package`` directory next to
       the skill bundle (dev convenience).
    """
    env_val = os.environ.get("VIBECODE_UPDATE_PACKAGE")
    if env_val:
        p = Path(env_val)
        return [p] if p.is_dir() else []
    for cand in (SKILL_ROOT.parent / "update",
                 SKILL_ROOT.parent / "update-package"):
        if cand.is_dir():
            return [cand]
    return []


# Docs that describe the *current* release and must stay in sync.
CURRENT_DOCS = [
    SKILL_ROOT / "SKILL.md",
    SKILL_ROOT / "QUICKSTART.md",
    SKILL_ROOT / "USAGE_GUIDE.md",
    SKILL_ROOT / "README.md",
]
for _up in _candidate_update_roots():
    for name in ("README.md", "QUICKSTART.md", "USAGE_GUIDE.md", "CLAUDE.md"):
        p = _up / name
        if p.is_file():
            CURRENT_DOCS.append(p)


STALE_PATTERNS = [
    # v0.10.x legacy counts.
    r"\b24 slash\b",
    r"\b39 / 39\b",
    r"\b39-probe\b",
    r"\b526 / 526\b",
    r"\b526 regression\b",
    r"\b284 passed\b",
    # REFINE-002 additions per reviewer spec.
    r"\b39 conformance probes\b",
    r"\b39 probes\b",
    r"\b39 runtime probes\b",
    r"\b526 tests\b",
    r"\b50/50 PASS\b",
    r"\b50/50 probes\b",
    r"\bv0\.11\.0 \(final\)",
    r"\bv0\.11\.2 \(final\)",
    r"\bVibecodeKit Hybrid Ultra v0\.11\.2\)",
    r"\bvibecodekit-hybrid-ultra-v0\.11\.0",
    r"\bvibecodekit-hybrid-ultra-v0\.11\.2",
    r"\b7 preset × 3 stacks\b",
    r"\b7 preset × 3 stack\b",
    r"\b7 preset bundled\b",
    # Intermediate v0.11.x probe counts (not historical-labelled).
    r"\b44-probe\b",
    r"\b44 / 44\b",
    r"\b47-probe\b",
    r"\b47 / 47\b",
    r"\b50-probe\b",
    r"\b50 / 50\b",
    # v0.11.4.1 freeze — guard against stale claims sneaking back in
    # after the v0.15.4 doc-sync (Finding B from post-merge audit).
    r"\b53-probe\b",
    r"\b53 probes?\b",
    r"\b53 / 53\b",
    r"\b53/53\b",
    r"\b53 conformance probes\b",
    r"\b367 passed\b",
    r"\b26 slash\b",
    r"\bcurrent: \*\*v0\.11\.4\.1\*\*",
    r"\bshipping runtime is \*\*v0\.11\.4\.1\*\*",
    r"\boverlay v0\.11\.4\.1\b",
    r"\bVibecodeKit Hybrid Ultra v0\.11\.4\.1\)",
    # REFINE-FINAL additions: previous-release version literals that
    # must not leak into current-release prose.
    r"canonical version string \(`0\.11\.[0-2]`\)",
    r"canonical version string \(`0\.11\.3`\)",
    r"shipping runtime is \*\*v0\.11\.3\*\*(?!\.\d)",
    r"out of the box on \*\*v0\.11\.3\*\*(?!\.\d)",
    r"Bản này ứng với\s*\n?\s*\*\*v0\.11\.0\*\* \(final\)",
    r"Bản này ứng với\s*\n?\s*\*\*v0\.11\.2\*\* \(final\)",
]


_CURRENT_VERSION = ""
_ver_file = SKILL_ROOT / "VERSION"
if _ver_file.is_file():
    _CURRENT_VERSION = _ver_file.read_text().strip()


def _is_historical_heading(heading: str) -> bool:
    """Heading text (without ``#``) is historical if:
    - it is explicitly tagged ``(historical)``; **or**
    - it **contains anywhere** a version literal (``v0.11.2`` /
      ``[0.11.2]`` / ``(v0.10.3 fix)`` / ``— gstack-port modules
      (v0.12.0–v0.15.0)``) and that version is **not** the current
      release.  Pre-PR2 chỉ match khi heading bắt đầu bằng version
      literal; PR2 mở rộng để các subsection kiểu
      ``### 12.3 Stdio (v0.10.2 fix)`` cũng được coi là historical.
    """
    stripped = heading.strip()
    if re.search(r"\(historical\)", stripped, re.IGNORECASE):
        return True
    for m in re.finditer(r"\bv?(0\.\d+(?:\.\d+)?)\b", stripped):
        ver = m.group(1)
        if ver != _CURRENT_VERSION and not _CURRENT_VERSION.startswith(ver):
            return True
    return False


def _strip_historical(body: str) -> str:
    """Drop content that is explicitly labelled as historical so the
    regex guard only flags forward-facing prose.

    Heuristics (PR2 expanded):
    1. Markdown sections whose heading is historical (per
       :func:`_is_historical_heading` — chứa bất kỳ version literal
       non-current hoặc tag ``(historical)``) are dropped in full.
       Skip levels are tracked với một **stack** để nested historical
       subsections (level 3 trong level 2) không "unskip" parent
       section khi sibling subsection kế tiếp không historical.
    2. Sections explicitly tagged ``(historical)`` are dropped.
    3. Table rows that start with ``| 0.x.y |`` or ``| v0.x.y |`` are
       changelog-style version history rows — dropped.
    4. Bullets kiểu ``- **vX.Y.Z** — ...`` (changelog-style entry list)
       được bỏ qua — đây là history list, không phải claim status.
    5. Nội dung trong fenced code block (``\`\`\` ... \`\`\```) được
       loại trừ vì thường là ví dụ / lệnh shell chứa tên file
       version-stamped (`vibecodekit-hybrid-ultra-vX.Y.Z-skill.zip`).
    """
    out: list[str] = []
    # Stack of section levels currently being skipped (outermost first).
    # Using a stack instead of a single int handles nested historical
    # sections correctly: when leaving a level-3 historical subsection
    # back into a level-3 sibling that is *not* historical, we still
    # respect the level-2 ancestor skip if that was historical.
    skip_stack: list[int] = []
    in_fence = False

    section_re = re.compile(r"^(#+)\s*(.*)$")
    table_row_re = re.compile(r"^\|\s*v?0\.\d+\.\d+\s*\|")
    fence_re = re.compile(r"^\s*```")
    cl_bullet_re = re.compile(r"^\s*[-*]\s+\*\*v?0\.\d+\.\d+")

    for line in body.splitlines():
        if fence_re.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        m = section_re.match(line)
        if m:
            hashes, heading_body = m.group(1), m.group(2)
            level = len(hashes)
            # Pop skip levels >= current (we've left those sections).
            while skip_stack and level <= skip_stack[-1]:
                skip_stack.pop()
            if _is_historical_heading(heading_body):
                skip_stack.append(level)
                continue

        if skip_stack:
            continue

        if table_row_re.match(line):
            continue

        if cl_bullet_re.match(line):
            continue

        out.append(line)

    return "\n".join(out)


@pytest.mark.parametrize("doc", [d for d in CURRENT_DOCS if d.exists()])
@pytest.mark.parametrize("pattern", STALE_PATTERNS)
def test_no_stale_release_counts(doc: Path, pattern: str) -> None:
    body = _strip_historical(doc.read_text(encoding="utf-8"))
    matches = [m.group(0) for m in re.finditer(pattern, body)]
    assert not matches, (
        f"stale release-count substring {pattern!r} appears in {doc.name} "
        f"outside historical changelog entries: {matches}"
    )


# --- PR2: drift guard cho version literal forward-facing -------------
# Mục tiêu: bất kỳ literal version `v0.10.x`–`v0.16.x` nào xuất hiện
# trong prose forward-facing (ngoài section "Historical" / "Changelog",
# ngoài fenced code block, ngoài table version-history) đều bị flag.
# Chỉ literal `v<CURRENT_VERSION>` được phép vì nó nói trạng thái hiện tại.
# Test này khiến lần drift số liệu / version anchor tiếp theo (vd. khi
# bump v0.16.2 → v0.17.0 mà quên cập nhật prose) bị CI chặn ngay.

_VERSION_LITERAL_PATTERN = re.compile(r"\bv0\.1[0-6]\.\d+\b")


@pytest.mark.parametrize("doc", [d for d in CURRENT_DOCS if d.exists()])
def test_no_stale_version_literals_in_forward_prose(doc: Path) -> None:
    body = _strip_historical(doc.read_text(encoding="utf-8"))
    bad: list[tuple[int, str]] = []
    for ln_no, line in enumerate(body.splitlines(), 1):
        for m in _VERSION_LITERAL_PATTERN.finditer(line):
            literal = m.group(0)
            ver = literal[1:]  # bỏ chữ 'v'
            # Literal == current version là chấp nhận được (đang nói
            # trạng thái hiện tại); mọi literal version khác trong
            # forward-facing prose phải được wrap (historical) hoặc
            # đẩy vào CHANGELOG.md.
            if ver == _CURRENT_VERSION:
                continue
            bad.append((ln_no, line.rstrip()))
    assert not bad, (
        f"Stale forward-facing version literals detected in {doc.name}.\n"
        f"  Mỗi dòng dưới đây mention một version != {_CURRENT_VERSION!r} "
        f"trong prose ngoài section/heading historical.  Cách fix:\n"
        f"  - Wrap parent heading bằng `(historical)` hoặc đặt heading\n"
        f"    chứa version literal non-current; HOẶC\n"
        f"  - Bỏ literal khỏi dòng đó (ưu tiên tham chiếu CHANGELOG.md);\n"
        f"    HOẶC chuyển dòng đó thành code block / table changelog row.\n"
        + "\n".join(f"    L{ln}: {txt[:120]}" for ln, txt in bad)
    )


def test_changelog_top_section_is_current() -> None:
    """Confirm the top-of-CHANGELOG.md section really is the current
    release and doesn't accidentally carry forward stale summaries."""
    changelog = SKILL_ROOT / "CHANGELOG.md"
    if not changelog.is_file():
        pytest.skip("no CHANGELOG.md")
    body = changelog.read_text(encoding="utf-8")
    top = []
    header_seen = False
    for line in body.splitlines():
        if re.match(r"^##+\s+(\[)?v?0\.\d+\.\d+", line):
            if header_seen:
                break
            header_seen = True
            top.append(line)
            continue
        if header_seen:
            top.append(line)
    top_text = "\n".join(top)
    # The top section should mention the current VERSION.
    version = (SKILL_ROOT / "VERSION").read_text().strip() if (SKILL_ROOT / "VERSION").exists() else ""
    if version:
        assert version in top_text, (
            f"CHANGELOG.md top section does not mention current VERSION {version!r}"
        )


# --- REFINE-FINAL: metadata version sync ------------------------------
# Every shipped file that pins a version string must agree with
# ``skill-bundle/VERSION``.  This is a pure regression guard — if any
# of these drifts, CI fails loudly instead of releasing a mismatched
# bundle like the v0.11.3 → v0.11.3.1 drift the reviewer caught.

import json as _json
import sys

if sys.version_info >= (3, 11):
    import tomllib as _tomllib
else:
    _tomllib = None


def _extract_pyproject_version(p: Path) -> str:
    if _tomllib is not None:
        with open(p, "rb") as f:
            data = _tomllib.load(f)
        return data["project"]["version"]
    # Fallback for Python 3.9/3.10: regex extraction.
    text = p.read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    return m.group(1) if m else "<missing>"


def _extract_yaml_frontmatter_version(p: Path) -> str:
    """Extract ``version:`` from YAML frontmatter (between ``---`` fences)."""
    text = p.read_text(encoding="utf-8")
    in_fm = False
    for line in text.splitlines():
        if line.strip() == "---":
            if not in_fm:
                in_fm = True
                continue
            else:
                break
        if in_fm:
            m = re.match(r"^version:\s*(.+)$", line)
            if m:
                return m.group(1).strip()
    return "<missing>"


def _load_version_strict() -> str:
    """Match the canonical 4-segment VibecodeKit version *or* a PEP 440
    pre-release suffix (``aN`` / ``bN`` / ``rcN``), as used by
    v0.16.0-alpha (`0.16.0a0`) etc.  Anything richer than this (epochs,
    local segments) is rejected so we still catch typos."""
    ver = (SKILL_ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert re.fullmatch(
        r"\d+\.\d+\.\d+(?:\.\d+)?(?:(?:a|b|rc)\d+)?",
        ver,
    ), f"bad VERSION: {ver!r}"
    return ver


_METADATA_VERSION_SOURCES = [
    # (label, path-relative-to-skill-root, extractor)
    ("skill/VERSION",
     SKILL_ROOT / "VERSION",
     lambda p: p.read_text(encoding="utf-8").strip()),
    ("skill/assets/plugin-manifest.json#version",
     SKILL_ROOT / "assets" / "plugin-manifest.json",
     lambda p: _json.loads(p.read_text(encoding="utf-8"))["version"]),
    ("skill/manifest.llm.json#version",
     SKILL_ROOT / "manifest.llm.json",
     lambda p: _json.loads(p.read_text(encoding="utf-8")).get("version", "<missing>")),
    ("skill/pyproject.toml#project.version",
     SKILL_ROOT / "pyproject.toml",
     _extract_pyproject_version),
    ("skill/SKILL.md#frontmatter.version",
     SKILL_ROOT / "SKILL.md",
     _extract_yaml_frontmatter_version),
]
# Pull in update-package metadata too if the package can be located.
for _up in _candidate_update_roots():
    _METADATA_VERSION_SOURCES.extend([
        (f"{_up.name}/VERSION",
         _up / "VERSION",
         lambda p: p.read_text(encoding="utf-8").strip()),
        (f"{_up.name}/.claw.json#version",
         _up / ".claw.json",
         lambda p: _json.loads(p.read_text(encoding="utf-8"))["version"]),
    ])
    _vck_pipeline = _up / ".claude" / "commands" / "vck-pipeline.md"
    if _vck_pipeline.is_file():
        _METADATA_VERSION_SOURCES.append((
            f"{_up.name}/.claude/commands/vck-pipeline.md#frontmatter.version",
            _vck_pipeline,
            _extract_yaml_frontmatter_version,
        ))


@pytest.mark.parametrize("label,path,extractor",
                         [s for s in _METADATA_VERSION_SOURCES
                          if s[1].is_file()],
                         ids=[s[0] for s in _METADATA_VERSION_SOURCES
                              if s[1].is_file()])
def test_metadata_version_matches_canonical(label: str, path: Path, extractor) -> None:
    canonical = _load_version_strict()
    got = extractor(path)
    assert got == canonical, (
        f"{label} reports {got!r} but canonical skill/VERSION is {canonical!r}"
        )


def test_runtime_version_matches_canonical_VERSION_file() -> None:
    """The importable ``vibecodekit.VERSION`` must match the repo's
    ``VERSION`` file.  Catches stale ``_FALLBACK_VERSION`` regressions."""
    canonical = (SKILL_ROOT / "VERSION").read_text(encoding="utf-8").strip()
    import importlib, sys
    # Ensure a fresh import if already cached.
    mod_name = "vibecodekit"
    if mod_name in sys.modules:
        importlib.reload(sys.modules[mod_name])
    else:
        importlib.import_module(mod_name)
    runtime_version = sys.modules[mod_name].VERSION
    assert runtime_version == canonical, (
        f"vibecodekit.VERSION is {runtime_version!r} but "
        f"canonical VERSION file says {canonical!r}"
    )
