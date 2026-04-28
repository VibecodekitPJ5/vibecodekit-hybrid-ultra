"""learnings — per-project JSONL learning store.

A lightweight, stdlib-only append-log that captures a lesson (text,
tags, author, scope) whenever the operator runs ``/vck-learn``.
``load`` replays the store on session start so the host can inject
prior learnings into the system prompt.

Scope hierarchy matches :mod:`memory_hierarchy`::

  user    — ``~/.vibecode/learnings.jsonl``         (cross-project)
  project — ``.vibecode/learnings.jsonl``           (repo-local)
  team    — ``.vibecode/learnings.team.jsonl``      (committed)

Writes are atomic (tmp + os.replace) and fcntl-locked — two Devin
sessions writing to the same store will not corrupt the log.  This
reuses :mod:`_platform_lock` so Windows hosts fall through to a
no-op lock gracefully.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

from . import _platform_lock

__all__ = [
    "Learning",
    "LearningStore",
    "user_store",
    "project_store",
    "team_store",
    "load_all",
    "capture",
]

SCOPES = ("user", "project", "team")


@dataclass(frozen=True)
class Learning:
    """One learning entry."""
    text: str
    scope: str = "project"
    tags: Sequence[str] = field(default_factory=tuple)
    author: str = ""
    captured_ts: float = 0.0

    def as_dict(self) -> dict:
        d = asdict(self)
        d["tags"] = list(self.tags)
        return d

    @classmethod
    def from_dict(cls, raw: dict) -> "Learning":
        return cls(
            text=str(raw.get("text", "")),
            scope=str(raw.get("scope", "project")),
            tags=tuple(raw.get("tags") or ()),
            author=str(raw.get("author", "")),
            captured_ts=float(raw.get("captured_ts") or 0.0),
        )


class LearningStore:
    """Append-only JSONL store for a single scope."""

    def __init__(self, path: Path | str, scope: str = "project") -> None:
        if scope not in SCOPES:
            raise ValueError(f"bad scope {scope!r}; want one of {SCOPES}")
        self._path = Path(path)
        self._scope = scope

    @property
    def path(self) -> Path:
        return self._path

    @property
    def scope(self) -> str:
        return self._scope

    def append(self, learning: Learning) -> Learning:
        """Append one learning; returns the persisted record (with timestamp filled)."""
        if learning.captured_ts == 0.0:
            learning = Learning(
                text=learning.text, scope=self._scope,
                tags=tuple(learning.tags), author=learning.author,
                captured_ts=time.time(),
            )
        self._path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic append under fcntl lock.
        lock_path = self._path.with_suffix(self._path.suffix + ".lock")
        lock_fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o600)
        try:
            with _platform_lock.file_lock(lock_fd):
                line = json.dumps(learning.as_dict(), ensure_ascii=False) + "\n"
                with open(self._path, "a", encoding="utf-8") as f:
                    f.write(line)
                    f.flush()
                    try:
                        os.fsync(f.fileno())
                    except OSError:
                        pass
        finally:
            os.close(lock_fd)
        return learning

    def load(self) -> List[Learning]:
        if not self._path.is_file():
            return []
        out: List[Learning] = []
        with open(self._path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(Learning.from_dict(json.loads(line)))
                except (json.JSONDecodeError, TypeError, ValueError):
                    continue
        return out

    def clear(self) -> None:
        """Delete the log.  Used by tests only."""
        if self._path.exists():
            self._path.unlink()


# ---------------------------------------------------------------------------
# Scope-specific helpers
# ---------------------------------------------------------------------------

def user_store(home: Optional[Path] = None) -> LearningStore:
    home = home or Path(os.environ.get("VIBECODE_HOME") or Path.home() / ".vibecode")
    return LearningStore(home / "learnings.jsonl", scope="user")


def project_store(root: Optional[Path] = None) -> LearningStore:
    root = Path(root or Path.cwd())
    return LearningStore(root / ".vibecode" / "learnings.jsonl", scope="project")


def team_store(root: Optional[Path] = None) -> LearningStore:
    root = Path(root or Path.cwd())
    return LearningStore(root / ".vibecode" / "learnings.team.jsonl", scope="team")


def load_all(root: Optional[Path] = None,
             home: Optional[Path] = None) -> List[Learning]:
    """Merge user + team + project learnings (project last, overrides nothing)."""
    out: List[Learning] = []
    out.extend(user_store(home).load())
    out.extend(team_store(root).load())
    out.extend(project_store(root).load())
    return out


def capture(text: str,
            scope: str = "project",
            tags: Sequence[str] = (),
            author: str = "",
            root: Optional[Path] = None,
            home: Optional[Path] = None) -> Learning:
    """Convenience: append to the right store given a scope."""
    store: LearningStore
    if scope == "user":
        store = user_store(home)
    elif scope == "team":
        store = team_store(root)
    else:
        store = project_store(root)
    return store.append(Learning(text=text, scope=scope, tags=tuple(tags),
                                 author=author))


# ---------------------------------------------------------------------------
# CLI helper: vibe learnings {capture|list|clear}
# ---------------------------------------------------------------------------

def _main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Per-project learnings store")
    sub = ap.add_subparsers(dest="cmd", required=True)

    cap = sub.add_parser("capture", help="Append one learning.")
    cap.add_argument("--scope", default="project", choices=SCOPES)
    cap.add_argument("--tag", action="append", default=[])
    cap.add_argument("--author", default="")
    cap.add_argument("text", nargs="+")

    lst = sub.add_parser("list", help="List merged learnings.")
    lst.add_argument("--scope", default=None, choices=SCOPES)
    lst.add_argument("--json", action="store_true")

    sub.add_parser("clear", help="Clear project store (not user/team).")

    args = ap.parse_args(argv)

    if args.cmd == "capture":
        rec = capture(
            " ".join(args.text), scope=args.scope,
            tags=args.tag, author=args.author,
        )
        print(json.dumps(rec.as_dict(), ensure_ascii=False))
        return 0
    if args.cmd == "list":
        if args.scope == "user":
            items = user_store().load()
        elif args.scope == "team":
            items = team_store().load()
        elif args.scope == "project":
            items = project_store().load()
        else:
            items = load_all()
        if args.json:
            print(json.dumps([i.as_dict() for i in items], ensure_ascii=False, indent=2))
        else:
            for it in items:
                ts = time.strftime("%Y-%m-%d", time.localtime(it.captured_ts))
                print(f"[{ts}] ({it.scope}) {it.text}")
        return 0
    if args.cmd == "clear":
        project_store().clear()
        print("project learnings cleared")
        return 0
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
