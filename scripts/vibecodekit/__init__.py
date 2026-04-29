"""VibecodeKit Hybrid Ultra v0.15.5 — Full Agentic OS Runtime + Methodology Overlay.

Runtime layer: 30 probes corresponding 1:1 to the architectural patterns from
"Giải phẫu một Agentic Operating System" (Lâm Nguyễn, 2026) —
async generator loop, five-layer context defence, 7 task kinds,
4-phase DreamTask, MCP stdio, 33 hook events, cost ledger,
cross-platform (fcntl/msvcrt) locked denial store, 3-tier memory
hierarchy with pluggable embedding, approval/elicitation JSON contract,
follow-up re-execute loop, conditional skill activation.

Methodology layer: 9 extra probes exercising RRI (Reverse Requirements
Interview), RRI-T (7-dim testing × 8-stress-axis), RRI-UX (Flow Physics),
RRI-UI (4-phase pipeline), VIBECODE-MASTER workflow, Vietnamese
12-item checklist, and the 6 methodology slash-commands.

Public API is exposed via the ``cli`` module (``python -m vibecodekit.cli``)
and via the command-line scripts installed under ``ai-rules/vibecodekit/bin``.

Version resolution (added in v0.10.3.1 hardening):

``__version__`` is single-sourced from the bundle's ``VERSION`` file when
available (same directory as ``SKILL.md``); falls back to the hard-coded
string below when running from a location that doesn't have ``VERSION``
(e.g. a partial copy).  Use ``vibecodekit.VERSION`` for the resolved
value and ``vibecodekit.__version__`` for the same (alias).
"""
from __future__ import annotations

import os as _os
from pathlib import Path as _Path

_FALLBACK_VERSION = "0.15.5"


def _resolve_version() -> str:
    """Resolve version from bundle's ``VERSION`` file, with fallback.

    Walks upward from this module's directory looking for a ``VERSION``
    file co-located with ``SKILL.md`` (i.e. the skill bundle root).
    """
    here = _Path(__file__).resolve().parent  # .../scripts/vibecodekit
    candidates = [
        here.parent.parent / "VERSION",           # skill/vibecodekit-hybrid-ultra/VERSION
        here.parent.parent.parent / "VERSION",    # repo root VERSION (dev checkout)
    ]
    for p in candidates:
        try:
            if p.is_file():
                v = p.read_text(encoding="utf-8").strip()
                if v:
                    return v
        except OSError:
            continue
    return _FALLBACK_VERSION


__version__ = _resolve_version()
VERSION = __version__

__all__ = ["__version__", "VERSION"]
