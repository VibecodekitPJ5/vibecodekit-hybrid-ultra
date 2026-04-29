#!/usr/bin/env python3
"""Sync the canonical VERSION file to all mirror surfaces.

Usage:
    echo "0.17.0" > VERSION
    python tools/sync_version.py

Reads ``VERSION`` (repo root) and writes it into every mirror surface.
Run ``pytest tests/test_docs_count_sync.py`` afterwards to verify.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read_canonical() -> str:
    ver = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:\.\d+)?(?:(?:a|b|rc)\d+)?", ver):
        sys.exit(f"ERROR: bad VERSION format: {ver!r}")
    return ver


def _patch_plain(path: Path, version: str) -> bool:
    if not path.is_file():
        return False
    path.write_text(version + "\n", encoding="utf-8")
    return True


def _patch_json_version(path: Path, version: str) -> bool:
    if not path.is_file():
        return False
    data = json.loads(path.read_text(encoding="utf-8"))
    data["version"] = version
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def _patch_toml_version(path: Path, version: str) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    new_text = re.sub(
        r'^(version\s*=\s*")([^"]+)(")',
        rf'\g<1>{version}\3',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if new_text == text:
        print(f"  WARNING: no version= line found in {path}")
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


def _patch_yaml_frontmatter_version(path: Path, version: str) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    new_text = re.sub(
        r'^(version:\s*)(.+)$',
        rf'\g<1>{version}',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if new_text == text:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


def main() -> None:
    version = _read_canonical()
    print(f"Syncing version {version!r} from VERSION to all mirrors...")

    mirrors = [
        ("update-package/VERSION", lambda: _patch_plain(REPO_ROOT / "update-package" / "VERSION", version)),
        ("pyproject.toml", lambda: _patch_toml_version(REPO_ROOT / "pyproject.toml", version)),
        ("manifest.llm.json", lambda: _patch_json_version(REPO_ROOT / "manifest.llm.json", version)),
        ("assets/plugin-manifest.json", lambda: _patch_json_version(REPO_ROOT / "assets" / "plugin-manifest.json", version)),
        ("update-package/.claw.json", lambda: _patch_json_version(REPO_ROOT / "update-package" / ".claw.json", version)),
        ("SKILL.md", lambda: _patch_yaml_frontmatter_version(REPO_ROOT / "SKILL.md", version)),
        ("update-package/.claude/commands/vck-pipeline.md", lambda: _patch_yaml_frontmatter_version(
            REPO_ROOT / "update-package" / ".claude" / "commands" / "vck-pipeline.md", version)),
    ]

    for label, action in mirrors:
        ok = action()
        status = "OK" if ok else "SKIP (not found)"
        print(f"  {label}: {status}")

    print(f"\nDone. Run `pytest tests/test_docs_count_sync.py -v` to verify.")


if __name__ == "__main__":
    main()
