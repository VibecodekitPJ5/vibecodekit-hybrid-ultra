"""Pre-packaging validation for VibecodeKit releases.

Run this **before** zipping to fail fast on version drift, missing files,
or leaked build artefacts.  Exits 0 on success, 1 on any finding.

Usage::

    python tools/validate_release.py
    python tools/validate_release.py --repo /path/to/repo  # custom path

Checks:

1. ``VERSION`` exists + parses as semver (X.Y.Z).
2. Every version string in the codebase matches ``VERSION``:
   - ``skill/.../SKILL.md`` front-matter
   - ``skill/.../scripts/vibecodekit/__init__.py`` _FALLBACK_VERSION
   - ``skill/.../assets/plugin-manifest.json`` version
   - ``skill/.../scripts/vibecodekit/mcp_client.py`` client_version default
   - ``skill/.../scripts/vibecodekit/mcp_servers/selfcheck.py`` serverInfo.version
   - ``claw-code-pack/.claw.json`` version
   - ``claw-code-pack/CLAUDE.md`` header
   - ``claw-code-pack/README.md`` title + zip name + release gate
3. Required files exist in both skill bundle and update-package:
   - ``VERSION``
   - ``QUICKSTART.md``
   - ``tests/test_end_to_end_install.py`` (skill only)
4. No build junk inside bundles:
   - No ``__pycache__`` directories
   - No ``*.pyc`` files
   - No ``.vibecode/`` runtime state
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List, Tuple


def _ok(msg: str) -> None:
    print(f"  [OK]    {msg}")


def _fail(msg: str) -> None:
    print(f"  [FAIL]  {msg}")


def validate(repo: Path) -> int:
    findings: List[str] = []
    skill = repo / "skill" / "vibecodekit-hybrid-ultra"
    pack = repo / "claw-code-pack"

    # 1. VERSION file --------------------------------------------------------
    print("[1/4] VERSION file")
    vfile = repo / "VERSION"
    if not vfile.is_file():
        findings.append("missing VERSION file at repo root")
        _fail("VERSION missing")
        return 1
    canonical = vfile.read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", canonical):
        findings.append(f"VERSION not semver: {canonical!r}")
        _fail(f"VERSION not semver: {canonical!r}")
        return 1
    _ok(f"canonical version = {canonical}")

    # 2. Version sync across files ------------------------------------------
    print("[2/4] Version sync")
    checks: List[Tuple[str, Path, re.Pattern, int]] = [
        ("SKILL.md front-matter", skill / "SKILL.md",
         re.compile(r"^version:\s*([0-9.]+)", re.MULTILINE), 1),
        ("__init__.py _FALLBACK_VERSION",
         skill / "scripts" / "vibecodekit" / "__init__.py",
         re.compile(r'_FALLBACK_VERSION\s*=\s*"([^"]+)"'), 1),
        ("plugin-manifest.json version",
         skill / "assets" / "plugin-manifest.json",
         re.compile(r'"version":\s*"([^"]+)"'), 1),
        ("mcp_client client_version default",
         skill / "scripts" / "vibecodekit" / "mcp_client.py",
         re.compile(r'client_version:\s*str\s*=\s*"([^"]+)"'), 1),
        ("selfcheck serverInfo.version",
         skill / "scripts" / "vibecodekit" / "mcp_servers" / "selfcheck.py",
         re.compile(r'"vibecodekit-selfcheck",\s*"version":\s*"([^"]+)"'), 1),
        (".claw.json version", pack / ".claw.json",
         re.compile(r'"version":\s*"([^"]+)"'), 1),
    ]
    for name, path, pat, grp in checks:
        if not path.is_file():
            findings.append(f"{name}: missing file {path}")
            _fail(f"{name}: missing file")
            continue
        m = pat.search(path.read_text(encoding="utf-8"))
        if not m:
            findings.append(f"{name}: pattern did not match in {path}")
            _fail(f"{name}: no match")
            continue
        if m.group(grp) != canonical:
            findings.append(
                f"{name}: version {m.group(grp)!r} != canonical {canonical!r} "
                f"(in {path.relative_to(repo)})"
            )
            _fail(f"{name}: {m.group(grp)!r} != {canonical!r}")
        else:
            _ok(f"{name}: {m.group(grp)}")

    # CLAUDE.md header (loose match)
    claude_md = pack / "CLAUDE.md"
    if claude_md.is_file():
        text = claude_md.read_text(encoding="utf-8")
        if f"v{canonical}" in text:
            _ok(f"CLAUDE.md mentions v{canonical}")
        else:
            findings.append(f"CLAUDE.md does not mention v{canonical}")
            _fail("CLAUDE.md: missing current version")
        stale_counts = [c for c in ("284/284", "277/277") if c in text]
        if stale_counts:
            findings.append(f"CLAUDE.md release gate stale: {stale_counts}")
            _fail(f"CLAUDE.md stale release-gate counts: {stale_counts}")

    # update-package README
    readme = pack / "README.md"
    if readme.is_file():
        text = readme.read_text(encoding="utf-8")
        if f"v{canonical}" not in text:
            findings.append(f"README.md does not mention v{canonical}")
            _fail("README.md: missing current version")
        else:
            _ok(f"README.md mentions v{canonical}")

    # 3. Required files ------------------------------------------------------
    print("[3/4] Required files")
    required_skill = [
        skill / "VERSION",
        skill / "QUICKSTART.md",
        skill / "USAGE_GUIDE.md",
        skill / "tests" / "test_end_to_end_install.py",
        # v0.10.5: bundle the pre-packaging validator so downstream forks
        # can re-run the same hygiene check without cloning the repo.
        skill / "tools" / "validate_release.py",
    ]
    required_pack = [
        pack / "VERSION",
        pack / "QUICKSTART.md",
        pack / "USAGE_GUIDE.md",
    ]
    for p in required_skill + required_pack:
        if p.is_file():
            _ok(f"{p.relative_to(repo)}")
        else:
            findings.append(f"required file missing: {p.relative_to(repo)}")
            _fail(f"missing: {p.relative_to(repo)}")

    # 4. Build junk ----------------------------------------------------------
    # v0.10.5: tightened to also catch .pytest_cache and any stray runtime
    # state (denials.json, denials.lock) that shouldn't ship.
    print("[4/4] Build junk")
    for root in (skill, pack):
        junk: List[Path] = []
        for sub in root.rglob("__pycache__"):
            junk.append(sub)
        for sub in root.rglob("*.pyc"):
            junk.append(sub)
        for sub in root.rglob(".pytest_cache"):
            if sub.is_dir():
                junk.append(sub)
        for sub in root.rglob(".vibecode"):
            if sub.is_dir():
                junk.append(sub)
        # Stray denial-store leftovers in case someone ran the runtime from
        # inside the skill tree (denials.json / denials.lock outside of
        # ``.vibecode/``).
        for pattern in ("denials.json", "denials.lock"):
            for sub in root.rglob(pattern):
                junk.append(sub)
        if junk:
            for j in junk:
                findings.append(f"build junk: {j.relative_to(repo)}")
                _fail(f"junk: {j.relative_to(repo)}")
        else:
            _ok(f"no junk in {root.relative_to(repo)}")

    # 5. (optional) Verify built zips themselves -----------------------------
    # v0.10.6: previously we only checked the source tree; if pytest or a
    # test run polluted the source *after* the clean step, junk could still
    # end up in the zip.  Now we also scan inside every zip we can find
    # under ``dist/`` whose name matches the canonical version.
    dist = repo / "dist"
    junk_rx = re.compile(
        r"(__pycache__|\.pyc$|\.pytest_cache/|\.vibecode/|denials\.(json|lock)$)"
    )
    if dist.is_dir():
        print("[5/5] Zip contents")
        import zipfile
        zips = sorted(dist.glob(f"*v{canonical}*.zip"))
        if not zips:
            _ok(f"no zips under dist/ yet (build pending)")
        for z in zips:
            junk_entries: List[str] = []
            try:
                with zipfile.ZipFile(z, "r") as zf:
                    for name in zf.namelist():
                        if junk_rx.search(name):
                            junk_entries.append(name)
            except zipfile.BadZipFile:
                findings.append(f"zip corrupt: {z.name}")
                _fail(f"corrupt: {z.name}")
                continue
            if junk_entries:
                for e in junk_entries[:5]:
                    findings.append(f"zip junk in {z.name}: {e}")
                    _fail(f"{z.name}: {e}")
                if len(junk_entries) > 5:
                    _fail(f"  … and {len(junk_entries)-5} more")
            else:
                _ok(f"{z.name} clean")

    # Summary ----------------------------------------------------------------
    print()
    if findings:
        print(f"VALIDATION FAILED — {len(findings)} finding(s):")
        for f in findings:
            print(f"  - {f}")
        return 1
    print(f"VALIDATION OK — version {canonical} ready to package")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    p.add_argument("--repo", default=None,
                   help="repo root (default: auto-detect from this script)")
    args = p.parse_args()
    repo = Path(args.repo) if args.repo else Path(__file__).resolve().parents[1]
    if not (repo / "VERSION").is_file():
        print(f"error: --repo {repo} does not contain a VERSION file")
        return 2
    return validate(repo)


if __name__ == "__main__":
    sys.exit(main())
