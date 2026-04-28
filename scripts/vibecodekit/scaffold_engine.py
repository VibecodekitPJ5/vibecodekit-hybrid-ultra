"""Scaffold engine (v0.11.0, Phase final — F1).

Generates a runnable starter project from one of N opinionated presets ×
M stacks.  Inspired by taw-kit's preset folder, extended:

- **Multi-stack**: each preset can have multiple stack variants (e.g.
  Next.js, FastAPI, Expo).
- **Conformance probe**: every preset declares a `success_criteria`
  list that ``ScaffoldEngine.verify()`` checks after `apply()`, so we
  catch template drift across releases.
- **Dry-run + diff**: ``preview()`` returns the file tree and estimated
  LOC without touching disk.
- **Manifest-driven**: presets are pure YAML/JSON-like dicts; no Python
  template logic in the bundle, so adding a preset is just adding a
  directory under ``assets/scaffolds/<preset-name>/``.

Public API::

    from vibecodekit.scaffold_engine import ScaffoldEngine
    engine = ScaffoldEngine()                       # auto-discovers presets
    engine.list_presets()                           # → list[PresetInfo]
    plan = engine.preview("landing-page", stack="nextjs")
    result = engine.apply("landing-page", "/tmp/my-site", stack="nextjs")
    engine.verify(result)                           # → list[Issue]

Preset directory layout::

    assets/scaffolds/<preset>/
        manifest.json       # required: name, description, stacks
        nextjs/             # one folder per stack variant
            <files...>      # files to copy verbatim
        fastapi/
            <files...>
        expo/
            <files...>

Manifest schema::

    {
      "name": "landing-page",
      "description": "Static marketing landing page with email capture",
      "stacks": {
        "nextjs": {
          "files": ["package.json", "app/page.tsx", "README.md"],
          "post_install": ["npm install", "npm run dev"],
          "success_criteria": [
            "package.json exists",
            "app/page.tsx exists",
            "package.json has 'next' in dependencies"
          ]
        },
        "fastapi": { ... }
      }
    }
"""
from __future__ import annotations

import dataclasses
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any, Iterable, Sequence


# ---------------------------------------------------------------------------
# Resolve scaffolds dir
# ---------------------------------------------------------------------------
def _default_scaffolds_dir() -> Path:
    """Locate the bundled ``assets/scaffolds/`` folder regardless of layout."""
    env = os.environ.get("VIBECODE_SKILL_ROOT")
    if env:
        return Path(env) / "assets" / "scaffolds"
    here = Path(__file__).resolve()
    # scripts/vibecodekit/this_file → up to skill root
    skill_root = here.parents[2]
    return skill_root / "assets" / "scaffolds"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------
@dataclasses.dataclass(frozen=True)
class PresetInfo:
    name: str
    description: str
    stacks: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class ScaffoldFile:
    rel_path: str
    bytes: int


@dataclasses.dataclass(frozen=True)
class ScaffoldPlan:
    preset: str
    stack: str
    target_dir: Path
    files: tuple[ScaffoldFile, ...]
    post_install: tuple[str, ...]
    success_criteria: tuple[str, ...]
    estimated_loc: int


@dataclasses.dataclass(frozen=True)
class ScaffoldResult:
    preset: str
    stack: str
    target_dir: Path
    files_written: tuple[str, ...]
    bytes_written: int
    success_criteria: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class Issue:
    file: str
    message: str


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
class ScaffoldEngine:
    """Driver-less scaffold engine — manifest + file copy."""

    def __init__(self, scaffolds_dir: os.PathLike[str] | str | None = None):
        self.dir = Path(scaffolds_dir) if scaffolds_dir else _default_scaffolds_dir()

    # -- discovery --------------------------------------------------------
    def list_presets(self) -> list[PresetInfo]:
        out: list[PresetInfo] = []
        if not self.dir.is_dir():
            return out
        for p in sorted(self.dir.iterdir()):
            if not p.is_dir():
                continue
            manifest = p / "manifest.json"
            if not manifest.is_file():
                continue
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            stacks = tuple(sorted((data.get("stacks") or {}).keys()))
            if not stacks:
                continue
            out.append(PresetInfo(
                name=data.get("name", p.name),
                description=data.get("description", ""),
                stacks=stacks,
            ))
        return out

    def has_preset(self, name: str) -> bool:
        return any(p.name == name for p in self.list_presets())

    # -- internals --------------------------------------------------------
    def _read_manifest(self, preset: str) -> dict[str, Any]:
        manifest = self.dir / preset / "manifest.json"
        if not manifest.is_file():
            raise FileNotFoundError(f"unknown preset: {preset}")
        return json.loads(manifest.read_text(encoding="utf-8"))

    def _stack_spec(self, preset: str, stack: str) -> dict[str, Any]:
        data = self._read_manifest(preset)
        stacks = data.get("stacks") or {}
        if stack not in stacks:
            raise ValueError(
                f"preset {preset!r} has no stack {stack!r}; "
                f"available: {sorted(stacks)}"
            )
        return stacks[stack]

    def _stack_files_root(self, preset: str, stack: str) -> Path:
        return self.dir / preset / stack

    # -- plan / preview ---------------------------------------------------
    def preview(self, preset: str, stack: str,
                target_dir: os.PathLike[str] | str = ".") -> ScaffoldPlan:
        spec = self._stack_spec(preset, stack)
        root = self._stack_files_root(preset, stack)
        files: list[ScaffoldFile] = []
        loc = 0
        for rel in spec.get("files", []):
            src = root / rel
            if not src.is_file():
                raise FileNotFoundError(
                    f"preset {preset}/{stack} declares missing file: {rel}"
                )
            text = src.read_text(encoding="utf-8", errors="replace")
            files.append(ScaffoldFile(rel_path=rel, bytes=len(text.encode("utf-8"))))
            loc += text.count("\n") + 1
        return ScaffoldPlan(
            preset=preset,
            stack=stack,
            target_dir=Path(target_dir).resolve(),
            files=tuple(files),
            post_install=tuple(spec.get("post_install", [])),
            success_criteria=tuple(spec.get("success_criteria", [])),
            estimated_loc=loc,
        )

    # -- apply ------------------------------------------------------------
    def apply(self, preset: str, target_dir: os.PathLike[str] | str,
              stack: str, *, force: bool = False) -> ScaffoldResult:
        plan = self.preview(preset, stack, target_dir)
        target = plan.target_dir
        target.mkdir(parents=True, exist_ok=True)
        existing = [f for f in plan.files if (target / f.rel_path).exists()]
        if existing and not force:
            raise FileExistsError(
                f"target has {len(existing)} conflicting file(s) "
                f"(use force=True): "
                + ", ".join(f.rel_path for f in existing[:5])
                + ("…" if len(existing) > 5 else "")
            )

        root = self._stack_files_root(preset, stack)
        written: list[str] = []
        bytes_total = 0
        for f in plan.files:
            dest = target / f.rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / f.rel_path, dest)
            written.append(f.rel_path)
            bytes_total += f.bytes
        return ScaffoldResult(
            preset=preset,
            stack=stack,
            target_dir=target,
            files_written=tuple(written),
            bytes_written=bytes_total,
            success_criteria=plan.success_criteria,
        )

    # -- verify -----------------------------------------------------------
    def verify(self, result: ScaffoldResult) -> list[Issue]:
        """Run preset-declared success criteria against the applied result."""
        issues: list[Issue] = []
        target = result.target_dir
        for crit in result.success_criteria:
            if not _check_criterion(crit, target):
                issues.append(Issue(file="-", message=f"failed: {crit}"))
        return issues


# ---------------------------------------------------------------------------
# Success-criterion mini-DSL
# ---------------------------------------------------------------------------
_PATH_EXISTS_RE = re.compile(r"^\s*(.+?)\s+exists\s*$", re.IGNORECASE)
_PATH_CONTAINS_RE = re.compile(
    r"^\s*(.+?)\s+contains\s+'(.*)'\s*$", re.IGNORECASE)
_JSON_HAS_DEP_RE = re.compile(
    r"^\s*(.+?)\s+has\s+'(.+?)'\s+in\s+(dependencies|devDependencies|scripts)\s*$",
    re.IGNORECASE,
)


def _check_criterion(criterion: str, target: Path) -> bool:
    m = _PATH_EXISTS_RE.match(criterion)
    if m:
        return (target / m.group(1).strip()).exists()
    m = _PATH_CONTAINS_RE.match(criterion)
    if m:
        path = target / m.group(1).strip()
        if not path.is_file():
            return False
        return m.group(2) in path.read_text(encoding="utf-8", errors="replace")
    m = _JSON_HAS_DEP_RE.match(criterion)
    if m:
        path = target / m.group(1).strip()
        key, section = m.group(2).strip(), m.group(3).strip()
        if not path.is_file():
            return False
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return False
        return key in (data.get(section) or {})
    # Unknown criterion → fail closed (preset author's bug).
    return False


__all__ = [
    "ScaffoldEngine",
    "PresetInfo",
    "ScaffoldFile",
    "ScaffoldPlan",
    "ScaffoldResult",
    "Issue",
]
