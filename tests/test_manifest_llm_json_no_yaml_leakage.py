"""Guard against YAML block-scalar markers leaking into manifest.llm.json.

``>-``, ``|-``, ``>``, ``|``, ``>+``, ``|+`` are YAML folding/literal
indicators that have no meaning in JSON.  If they appear as string
values it means the YAML→JSON serialisation was incorrect.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "manifest.llm.json"

_YAML_BLOCK_SCALARS = {">-", "|-", ">", "|", ">+", "|+"}


def _walk(obj: object, prefix: str = "$") -> Iterator[tuple[str, object]]:
    """Yield ``(json-path, value)`` for every leaf in a JSON structure."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk(v, f"{prefix}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk(v, f"{prefix}[{i}]")
    else:
        yield prefix, obj


def test_manifest_llm_json_has_no_yaml_block_scalar_markers():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    bad: list[str] = []
    for path, value in _walk(data):
        if isinstance(value, str):
            stripped = value.strip()
            if stripped in _YAML_BLOCK_SCALARS:
                bad.append(f"{path}: {value!r}")
    assert not bad, (
        "YAML block-scalar markers leaked into manifest.llm.json:\n"
        + "\n".join(f"  - {b}" for b in bad)
    )


def test_manifest_llm_json_no_suspiciously_short_descriptions():
    """Top-level description and skill_frontmatter.when_to_use should be
    meaningful sentences, not stubs."""
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for key in ("description",):
        val = data.get(key, "")
        assert len(val) > 10, f"$.{key} is suspiciously short: {val!r}"
    fm = data.get("skill_frontmatter", {})
    for key in ("when_to_use",):
        val = fm.get(key, "")
        assert len(val) > 10, f"$.skill_frontmatter.{key} is suspiciously short: {val!r}"
