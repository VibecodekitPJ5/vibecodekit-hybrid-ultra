"""Guard cho frontmatter ``deprecated: true`` trong slash command.

Khi mark m\u1ed9t command l\u00e0 deprecated, ph\u1ea3i ghi r\u00f5 canonical thay th\u1ebf
(``replaced-by``) v\u00e0 m\u1ed1c remove (``removal-target``).  Test n\u00e0y kh\u00f3a
3 invariant:

1. M\u1ecdi file ``.md`` trong ``update-package/.claude/commands/`` c\u00f3
   ``deprecated: true`` PH\u1ea2I c\u00f3 c\u1ea3 ``replaced-by`` v\u00e0
   ``removal-target``.
2. ``replaced-by`` ph\u1ea3i tr\u1ecf t\u1edbi m\u1ed9t canonical command \u0111ang t\u1ed3n
   t\u1ea1i (file ``.md`` cho command \u0111\u00f3 ph\u1ea3i n\u1eb1m c\u00f9ng th\u01b0 m\u1ee5c).
3. Canonical command \u0111\u00f3 ph\u1ea3i KH\u00d4NG \u0111\u01b0\u1ee3c \u0111\u00e1nh ``deprecated:
   true`` (ng\u0103n ch\u1eb7n ch\u1eddi r\u1eddi: A \u2192 B \u2192 C trong khi B c\u0169ng
   deprecated).

Hi\u1ec7n c\u00f3 5 deprecate marker (4 t\u1eeb PR4 + 1 t\u1eeb PR5):
    /vibe-ship      \u2192 /vck-ship   (canonical: /vck-ship full pipeline)
    /vibe-rri-t     \u2192 /vibe-rri   (canonical: /vibe-rri 5-persona)
    /vibe-rri-ui    \u2192 /vibe-rri
    /vibe-rri-ux    \u2192 /vibe-rri
    /vck-qa-only    \u2192 /vck-qa     (canonical: /vck-qa full QA, exit
                                  code l\u00e0m vai tr\u00f2 CI gate; PR5)

KH\u00d4NG x\u00f3a file deprecated; KH\u00d4NG b\u1ecf entry kh\u1ecfi ``manifest.llm.json``
hay ``intent_router``.  5 file v\u1eabn invokable cho session c\u0169.

Soft-cap: m\u1ee5c ti\u00eau gi\u1eef \u2264 20 deprecated command (kho\u1ea3ng
50% surface ~41) \u0111\u1ec3 b\u1ea3o command surface kh\u00f4ng b\u1ecb pollution;
v\u01b0\u1ee3t cap \u2192 ph\u1ea3i th\u1ea3o lu\u1eadn v\u1edbi user.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
COMMANDS_DIR = REPO_ROOT / "update-package" / ".claude" / "commands"


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Parse YAML-ish frontmatter th\u00e0nh ``dict[str, str]``.

    Kh\u00f4ng pull v\u00e0o ``pyyaml`` \u0111\u1ec3 gi\u1eef test zero-dep.  Ch\u1ec9 \u0111\u1ecdc top-
    level scalar (``key: value``) v\u00e0 boolean ``true``/``false``; b\u1ecf qua
    block scalar (``key: |``).  \u0110\u1ee7 \u0111\u1ec3 ki\u1ec3m tra
    ``deprecated``/``replaced-by``/``removal-target``.
    """
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    block = text[4:end]
    out: dict[str, str] = {}
    skip_block_scalar_indent: int | None = None
    for line in block.splitlines():
        if skip_block_scalar_indent is not None:
            stripped = line.lstrip(" ")
            indent = len(line) - len(stripped)
            if line.strip() == "" or indent > skip_block_scalar_indent:
                continue
            skip_block_scalar_indent = None
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", line)
        if not m:
            continue
        key, raw = m.group(1), m.group(2).strip()
        if raw in ("|", "|-", "|+", ">", ">-", ">+"):
            indent = len(line) - len(line.lstrip(" "))
            skip_block_scalar_indent = indent
            out[key] = "<block scalar>"
            continue
        out[key] = raw.strip("\"'")
    return out


def _all_command_files() -> list[Path]:
    return sorted(p for p in COMMANDS_DIR.glob("*.md") if p.is_file())


def _command_name(path: Path) -> str:
    return "/" + path.stem


@pytest.fixture(scope="module")
def parsed_commands() -> dict[str, dict[str, str]]:
    return {
        _command_name(p): _parse_frontmatter(p.read_text(encoding="utf-8"))
        for p in _all_command_files()
    }


def test_deprecated_commands_have_replaced_by_and_removal_target(
    parsed_commands: dict[str, dict[str, str]],
) -> None:
    """Invariant 1: c\u1eb7p ``replaced-by`` + ``removal-target`` b\u1eaft bu\u1ed9c."""
    bad: list[tuple[str, list[str]]] = []
    for name, fm in parsed_commands.items():
        if fm.get("deprecated", "").lower() != "true":
            continue
        missing = [
            field
            for field in ("replaced-by", "removal-target")
            if not fm.get(field)
        ]
        if missing:
            bad.append((name, missing))
    assert not bad, (
        "Slash command marked ``deprecated: true`` mu\u1ed1n thi\u1ebfu field "
        "b\u1eaft bu\u1ed9c.  M\u1ed7i deprecate ph\u1ea3i ch\u1ec9 r\u00f5 canonical thay th\u1ebf + "
        "m\u1ed1c remove.\n"
        + "\n".join(
            f"  {name}: missing {', '.join(missing)}" for name, missing in bad
        )
    )


def test_deprecated_replaced_by_targets_exist(
    parsed_commands: dict[str, dict[str, str]],
) -> None:
    """Invariant 2: canonical ph\u1ea3i t\u1ed3n t\u1ea1i (file ``.md``)."""
    bad: list[tuple[str, str]] = []
    for name, fm in parsed_commands.items():
        if fm.get("deprecated", "").lower() != "true":
            continue
        target = fm.get("replaced-by", "").lstrip("/")
        if not target:
            continue
        target_file = COMMANDS_DIR / f"{target}.md"
        if not target_file.is_file():
            bad.append((name, fm.get("replaced-by", "")))
    assert not bad, (
        "Deprecated command \u0111ang tr\u1ecf t\u1edbi canonical kh\u00f4ng t\u1ed3n t\u1ea1i:\n"
        + "\n".join(f"  {name} \u2192 {tgt}" for name, tgt in bad)
    )


def test_deprecated_replaced_by_targets_are_not_themselves_deprecated(
    parsed_commands: dict[str, dict[str, str]],
) -> None:
    """Invariant 3: kh\u00f4ng cho ch\u1eddi A \u2192 B \u2192 C n\u1ebfu B c\u0169ng deprecated."""
    bad: list[tuple[str, str]] = []
    for name, fm in parsed_commands.items():
        if fm.get("deprecated", "").lower() != "true":
            continue
        target = fm.get("replaced-by", "")
        target_fm = parsed_commands.get(target, {})
        if target_fm.get("deprecated", "").lower() == "true":
            bad.append((name, target))
    assert not bad, (
        "Deprecated command tr\u1ecf t\u1edbi canonical c\u0169ng deprecated (chu\u1ed7i "
        "deprecate-of-deprecate):\n"
        + "\n".join(f"  {name} \u2192 {tgt} (also deprecated)" for name, tgt in bad)
    )


def test_known_deprecate_pairs_are_marked(
    parsed_commands: dict[str, dict[str, str]],
) -> None:
    """C\u1ed1 \u0111\u1ecbnh 4 c\u1eb7p deprecate \u0111\u00e3 thi\u1ebft k\u1ebf trong PR4 \u0111\u1ec3 tr\u00e1nh
    fall-back im l\u1eb7ng (vd. ai \u0111\u00f3 x\u00f3a frontmatter \u0111i)."""
    expected = {
        "/vibe-ship": "/vck-ship",
        "/vibe-rri-t": "/vibe-rri",
        "/vibe-rri-ui": "/vibe-rri",
        "/vibe-rri-ux": "/vibe-rri",
        "/vck-qa-only": "/vck-qa",
    }
    bad: list[str] = []
    for name, canonical in expected.items():
        fm = parsed_commands.get(name, {})
        if fm.get("deprecated", "").lower() != "true":
            bad.append(f"{name}: missing ``deprecated: true``")
            continue
        if fm.get("replaced-by") != canonical:
            bad.append(
                f"{name}: replaced-by={fm.get('replaced-by')!r}, "
                f"expect {canonical!r}"
            )
    assert not bad, "\n".join(bad)


def test_deprecated_command_count_within_soft_cap(
    parsed_commands: dict[str, dict[str, str]],
) -> None:
    """Soft-cap: \u2264 20 deprecated command (~50% surface ~41).

    M\u1ee5c \u0111\u00edch: tr\u00e1nh d\u00f9ng deprecate marker l\u00e0m
    clutter; n\u1ebfu surface th\u1eadt s\u1ef1 c\u1ea7n thu nh\u1ecf >50%
    th\u00ec ph\u1ea3i d\u1eebng l\u1ea1i th\u1ea3o lu\u1eadn v\u1edbi maintainer
    \u0111\u1ec3 quy\u1ebft \u0111\u1ecbnh x\u00f3a th\u1eadt thay v\u00ec
    deprecate hay kh\u00f4ng.

    Hi\u1ec7n PR5: 5 deprecated / 41 t\u1ed5ng \u2248 12%.
    """
    deprecated = [
        name
        for name, fm in parsed_commands.items()
        if fm.get("deprecated", "").lower() == "true"
    ]
    cap = 20
    assert len(deprecated) <= cap, (
        f"S\u1ed1 deprecated command ({len(deprecated)}) v\u01b0\u1ee3t "
        f"soft-cap ({cap}).  V\u01b0\u1ee3t cap = >50% surface ph\u1ea3i "
        f"deprecate \u2014 d\u1eebng l\u1ea1i th\u1ea3o lu\u1eadn v\u1edbi "
        f"maintainer.  Deprecated hi\u1ec7n t\u1ea1i: {sorted(deprecated)}"
    )
