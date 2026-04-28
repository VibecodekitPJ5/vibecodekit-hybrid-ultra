"""team_mode — team coordination flags stored in ``.vibecode/team.json``.

A minimal, stdlib-only coordination primitive for opt-in team mode.
``.vibecode/team.json`` carries:

- ``team_id``      — free-form identifier (e.g. "web-platform").
- ``required``     — slash commands every contributor MUST run before push
                     (e.g. ``/vck-review``, ``/vck-qa-only``).
- ``optional``     — advisory-only gates.
- ``learnings_required`` — if true, enforce ``/vck-learn`` at completion.
- ``created_ts`` / ``updated_ts``.

``vibe team-init`` (a new CLI subcommand wired via
:mod:`vibecodekit.cli`) writes the file.  Tools that enforce gates
(e.g. ``/vck-ship``) read it via :func:`read_team_config` and raise on
a missing required gate.

Inspired by gstack's ``teams.json`` concept — clean-room Python rewrite,
attribution in LICENSE-third-party.md.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

__all__ = [
    "TeamConfig",
    "TEAM_FILE",
    "read_team_config",
    "write_team_config",
    "is_team_mode",
    "assert_required_gates_run",
    "TeamGateViolation",
]

TEAM_FILE = ".vibecode/team.json"


class TeamGateViolation(RuntimeError):
    """Raised when a required team gate has not been satisfied."""


@dataclass(frozen=True)
class TeamConfig:
    team_id: str = ""
    required: Sequence[str] = field(default_factory=tuple)
    optional: Sequence[str] = field(default_factory=tuple)
    learnings_required: bool = False
    created_ts: float = 0.0
    updated_ts: float = 0.0

    def as_dict(self) -> dict:
        d = asdict(self)
        d["required"] = list(self.required)
        d["optional"] = list(self.optional)
        return d

    @classmethod
    def from_dict(cls, raw: dict) -> "TeamConfig":
        def _seq(value: object) -> tuple:
            # A bare string would be silently iterated as ("o", "o", "p", "s")
            # by ``tuple(value)``, which is a footgun for hand-edited JSON.
            # Reject strings explicitly; require a real list/tuple.
            if value is None:
                return ()
            if isinstance(value, (list, tuple)):
                return tuple(str(v) for v in value)
            raise ValueError(
                f"team config field expected list, got {type(value).__name__}: {value!r}"
            )
        return cls(
            team_id=str(raw.get("team_id", "")),
            required=_seq(raw.get("required")),
            optional=_seq(raw.get("optional")),
            learnings_required=bool(raw.get("learnings_required")),
            created_ts=float(raw.get("created_ts") or 0.0),
            updated_ts=float(raw.get("updated_ts") or 0.0),
        )


def _resolve(root: Optional[Path]) -> Path:
    return Path(root or Path.cwd()) / TEAM_FILE


def is_team_mode(root: Optional[Path] = None) -> bool:
    return _resolve(root).is_file()


def read_team_config(root: Optional[Path] = None) -> Optional[TeamConfig]:
    p = _resolve(root)
    if not p.is_file():
        return None
    try:
        return TeamConfig.from_dict(json.loads(p.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, ValueError, TypeError):
        # Malformed file (corrupt JSON or wrong field types) — treat as
        # "no team config" rather than crash the consumer.  Callers that
        # need to surface the error can call ``TeamConfig.from_dict``
        # directly.
        return None


def write_team_config(cfg: TeamConfig, root: Optional[Path] = None) -> TeamConfig:
    p = _resolve(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    now = time.time()
    if cfg.created_ts == 0.0 and not p.is_file():
        created = now
    else:
        prior = read_team_config(root)
        created = prior.created_ts if prior and prior.created_ts else now
    new = TeamConfig(
        team_id=cfg.team_id, required=tuple(cfg.required),
        optional=tuple(cfg.optional),
        learnings_required=cfg.learnings_required,
        created_ts=created, updated_ts=now,
    )
    # Use a per-writer unique tmp path so concurrent writers (e.g. two
    # Devin sessions running ``vibe team-init`` in parallel) do not race
    # on a shared ``team.json.tmp`` and crash with FileNotFoundError on
    # ``os.replace``.  ``mkstemp`` opens an FD we then close; the temp
    # file lives in the same directory so ``os.replace`` is atomic.
    fd, tmp_str = tempfile.mkstemp(
        prefix=p.name + ".", suffix=".tmp", dir=str(p.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(new.as_dict(), ensure_ascii=False, indent=2))
        try:
            os.chmod(tmp_str, 0o644)
        except OSError:
            pass
        os.replace(tmp_str, p)
    except Exception:
        # Best-effort cleanup if we crashed before the rename.
        try:
            os.unlink(tmp_str)
        except OSError:
            pass
        raise
    return new


def assert_required_gates_run(gates_run: Iterable[str],
                              root: Optional[Path] = None) -> None:
    """Raise :class:`TeamGateViolation` if team mode is on and any
    required gate was not found in ``gates_run``.  No-op otherwise.
    """
    cfg = read_team_config(root)
    if cfg is None:
        return
    required = set(cfg.required)
    missing = required - set(gates_run)
    if missing:
        raise TeamGateViolation(
            f"team mode ({cfg.team_id!r}) requires these gates but they "
            f"did not run: {sorted(missing)}"
        )


# ---------------------------------------------------------------------------
# CLI: vibe team-init
# ---------------------------------------------------------------------------

def _main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Team mode coordination")
    sub = ap.add_subparsers(dest="cmd", required=True)

    init = sub.add_parser("init", help="Create or update .vibecode/team.json")
    init.add_argument("--team-id", required=True)
    init.add_argument("--required", action="append", default=[],
                      help="Required gate (repeatable).  E.g. --required /vck-review")
    init.add_argument("--optional", action="append", default=[])
    init.add_argument("--learnings-required", action="store_true")

    show = sub.add_parser("show", help="Print the current team config as JSON")
    _ = show

    args = ap.parse_args(argv)
    if args.cmd == "init":
        cfg = TeamConfig(
            team_id=args.team_id,
            required=tuple(args.required),
            optional=tuple(args.optional),
            learnings_required=args.learnings_required,
        )
        new = write_team_config(cfg)
        print(json.dumps(new.as_dict(), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "show":
        cfg = read_team_config()
        if cfg is None:
            print("(no team config)")
            return 1
        print(json.dumps(cfg.as_dict(), ensure_ascii=False, indent=2))
        return 0
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
