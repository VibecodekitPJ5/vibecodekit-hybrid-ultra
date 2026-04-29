"""Test cho ``verb_router.route_verb`` v\u00e0 CLI ``vibe verb`` (PR5).

Khoa\u0301 4 invariant cu\u0309 a unified front-door:

1. **8 verb chu\u1ea9n map \u0111\u00fang slash command canonical** (table-driven).
2. **Canonical target t\u1ed3n t\u1ea1i**: m\u1ed7i target c\u00f3 file ``.md`` trong
   ``update-package/.claude/commands/``.
3. **Canonical target KH\u00d4NG \u0111\u01b0\u1ee3c ``deprecated: true``**: gi\u1eef cho
   front-door tr\u1ecf t\u1edbi command \u0111ang s\u1ed1ng (kh\u00f4ng route v\u00e0o tunnel
   deprecate).
4. **Args forward verbatim**: ``route_verb('ship', ['--prod'])`` tr\u1ea3
   ``['/vck-ship', '--prod']``; verb kh\u00f4ng h\u1ee3p l\u1ec7 raise
   ``UnknownVerbError``.

Plus test CLI ``vibe verb <name>`` outputs slash command + args c\u00f3
quote.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
COMMANDS_DIR = REPO_ROOT / "update-package" / ".claude" / "commands"

sys.path.insert(0, str(REPO_ROOT / "scripts"))

from vibecodekit import verb_router  # noqa: E402


# Cau\u0301 tru\u0301c expected: c\u00f4 \u0301\u0111i\u0323nh \u0111u\u0301ng 8 c\u1eb7p \u0111a\u0303 thi\u00ea\u0301t k\u00ea\u0301 trong
# verb_router._VERB_TO_COMMAND.  M\u1ed5 i ti\u00eau \u0111\u00ea\u0300 m\u01a1\u0301i ph\u1ea3i bo\u0309 sung
# \u0111\u00f4\u0300ng b\u00f4\u0323 ca\u0309 invariant + help_text (m\u00f4\u0309i sai 1 ch\u00f4\u0303 fail).
EXPECTED_VERBS: dict[str, str] = {
    "scan": "/vibe-scan",
    "plan": "/vibe-blueprint",
    "build": "/vibe-scaffold",
    "review": "/vck-review",
    "qa": "/vck-qa",
    "ship": "/vck-ship",
    "audit": "/vibe-audit",
    "doctor": "/vibe-doctor",
}


@pytest.mark.parametrize("verb,canonical", EXPECTED_VERBS.items())
def test_verb_routes_to_canonical(verb: str, canonical: str) -> None:
    assert verb_router.route_verb(verb) == [canonical]


def test_supported_verbs_match_expected() -> None:
    assert set(verb_router.SUPPORTED_VERBS) == set(EXPECTED_VERBS)


def test_route_verb_forwards_args() -> None:
    routed = verb_router.route_verb("ship", ["--target", "vercel", "--prod"])
    assert routed == ["/vck-ship", "--target", "vercel", "--prod"]


def test_route_verb_handles_empty_args() -> None:
    assert verb_router.route_verb("scan", []) == ["/vibe-scan"]
    assert verb_router.route_verb("scan", None) == ["/vibe-scan"]


def test_route_verb_is_case_insensitive() -> None:
    assert verb_router.route_verb("SHIP") == ["/vck-ship"]
    assert verb_router.route_verb("  Plan  ") == ["/vibe-blueprint"]


def test_unknown_verb_raises() -> None:
    with pytest.raises(verb_router.UnknownVerbError) as exc_info:
        verb_router.route_verb("bogus")
    msg = str(exc_info.value)
    assert "bogus" in msg
    # Tha\u0301p \u0111\u01b0\u1ee3c list 8 verb h\u01a1\u0323p l\u1ec7 trong message:
    for v in EXPECTED_VERBS:
        assert v in msg


def test_unknown_verb_inherits_value_error() -> None:
    """``UnknownVerbError`` subclass ``ValueError`` \u0111\u1ec3 caller cu\u0303 b\u1eaft
    ``except ValueError`` v\u1eabn ho\u1ea1t \u0111\u1ed9ng."""
    assert issubclass(verb_router.UnknownVerbError, ValueError)


def _command_file(slash: str) -> Path:
    return COMMANDS_DIR / f"{slash.lstrip('/')}.md"


@pytest.mark.parametrize("canonical", sorted(set(EXPECTED_VERBS.values())))
def test_canonical_command_file_exists(canonical: str) -> None:
    """Invariant 2: canonical command file ph\u1ea3i t\u1ed3n t\u1ea1i."""
    target = _command_file(canonical)
    assert target.is_file(), (
        f"Canonical {canonical} target {target} kh\u00f4ng t\u1ed3n t\u1ea1i \u2014 "
        "verb_router \u0111ang tr\u1ecf t\u1edbi command kh\u00f4ng c\u00f3."
    )


@pytest.mark.parametrize("canonical", sorted(set(EXPECTED_VERBS.values())))
def test_canonical_command_is_not_deprecated(canonical: str) -> None:
    """Invariant 3: canonical KH\u00d4NG \u0111\u01b0\u1ee3c ``deprecated: true``."""
    body = _command_file(canonical).read_text(encoding="utf-8")
    # Frontmatter parser nh\u1eb9 (kh\u00f4ng pull pyyaml):
    m = re.match(r"---\n(.*?)\n---\n", body, re.DOTALL)
    if not m:
        return  # kh\u00f4ng c\u00f3 frontmatter \u2192 ch\u1eafc ch\u1eafn kh\u00f4ng deprecated
    fm = m.group(1)
    is_deprecated = re.search(r"^deprecated\s*:\s*true\s*$", fm, re.M) is not None
    assert not is_deprecated, (
        f"Canonical {canonical} dang \u0111\u00e1nh ``deprecated: true`` \u2014 "
        "verb_router kh\u00f4ng \u0111\u01b0\u1ee3c route v\u00e0o tunnel deprecate."
    )


def test_help_text_lists_all_verbs() -> None:
    text = verb_router.help_text()
    for verb, canonical in EXPECTED_VERBS.items():
        assert verb in text, f"help_text thi\u1ebfu verb {verb!r}"
        assert canonical in text, f"help_text thi\u1ebfu canonical {canonical!r}"
    # Song ng\u1eef v\u1ea1ch r\u00f5:
    assert "VN:" in text
    assert "EN:" in text


def test_help_text_no_stale_deprecated_canonical() -> None:
    """help_text KH\u00d4NG \u0111\u01b0\u1ee3c \u0111\u1ec1 ngh\u1ecb ng\u01b0\u1eddi d\u00f9ng dispatch t\u1edbi
    /vibe-ship (deprecated PR4) \u2014 canonical cho ship la\u0300 /vck-ship."""
    text = verb_router.help_text()
    # \u0110\u01b0\u1ee3c ph\u00e9p mention /vibe-ship trong context "deprecated" /
    # backward compat; KH\u00d4NG \u0111\u01b0\u1ee3c list n\u00f3 trong b\u1ea3ng route.  Check
    # th\u00f4 b\u1eb1ng n\u01b0\u01a1\u0301c \u0111\u00f4i: t\u00f4 \u0301i \u0111a check ham\u0300m kh\u00f4ng map ``ship \u2192
    # /vibe-ship`` n\u01b0\u00f4\u0303a.
    assert re.search(r"^\s*ship\s+\u2192\s*/vibe-ship\b", text, re.M) is None


# ---- CLI integration tests ------------------------------------------


def _run_cli(*argv: str) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "vibecodekit.cli", "verb", *argv],
        env={
            **__import__("os").environ,
            "PYTHONPATH": str(REPO_ROOT / "scripts"),
        },
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_cli_verb_prints_help_when_no_args() -> None:
    code, out, _err = _run_cli()
    assert code == 0
    assert "/vibe <verb>" in out
    assert "scan" in out and "ship" in out


def test_cli_verb_outputs_canonical_command() -> None:
    code, out, _err = _run_cli("scan")
    assert code == 0
    assert out.strip() == "/vibe-scan"


def test_cli_verb_forwards_args_with_quoting() -> None:
    code, out, _err = _run_cli("ship", "--target", "vercel", "--prod")
    assert code == 0
    # shlex.quote KH\u00d4NG quote arg \u0111\u01a1n gi\u1ea3n \u2192 simple split OK:
    parts = out.strip().split()
    assert parts == ["/vck-ship", "--target", "vercel", "--prod"]


def test_cli_verb_unknown_returns_code_2() -> None:
    code, _out, err = _run_cli("bogus")
    assert code == 2
    assert "Unknown verb" in err
