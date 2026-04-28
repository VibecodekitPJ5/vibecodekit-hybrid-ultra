"""Context modifier chain (Pattern #6).

Mutation tools may return a ``modifier`` dict from their result; these are
applied *serially* (never concurrently) to evolve the shared context state.
The chain is intentionally minimal and pluggable — new kinds are registered
via ``register_modifier``.

References:
- ``references/06-context-modifier-chain.md``
- ``references/09-five-layer-context-defense.md``
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Callable, Dict, List, Tuple


_MODIFIERS: Dict[str, Callable[[Dict, Dict], Dict]] = {}


def register_modifier(kind: str):
    def deco(fn: Callable[[Dict, Dict], Dict]) -> Callable[[Dict, Dict], Dict]:
        _MODIFIERS[kind] = fn
        return fn
    return deco


@register_modifier("file_changed")
def _m_file_changed(ctx: Dict, mod: Dict) -> Dict:
    ctx.setdefault("files_changed", []).append(mod.get("path"))
    return ctx


@register_modifier("artifact")
def _m_artifact(ctx: Dict, mod: Dict) -> Dict:
    ctx.setdefault("artifacts", []).append({k: v for k, v in mod.items() if k != "kind"})
    return ctx


@register_modifier("memory_fact")
def _m_memory_fact(ctx: Dict, mod: Dict) -> Dict:
    ctx.setdefault("memory_facts", []).append(mod.get("text"))
    return ctx


@register_modifier("denial")
def _m_denial(ctx: Dict, mod: Dict) -> Dict:
    ctx.setdefault("denials", []).append({"action": mod.get("action"), "reason": mod.get("reason")})
    return ctx


@register_modifier("task_status")
def _m_task_status(ctx: Dict, mod: Dict) -> Dict:
    ctx.setdefault("task_status", {})[mod.get("task_id")] = mod.get("status")
    return ctx


def apply_modifiers(root: str | os.PathLike, context: Dict, modifiers: List[Dict]) -> Tuple[Dict, List[Dict]]:
    context = dict(context or {})
    applied: List[Dict] = []
    for mod in modifiers:
        fn = _MODIFIERS.get(mod.get("kind"))
        if fn is None:
            continue
        try:
            context = fn(context, mod)
            applied.append(mod)
        except Exception as e:  # pragma: no cover
            applied.append({"error": str(e), "modifier": mod})
    context["last_modifier_ts"] = time.time()
    out = Path(root) / ".vibecode" / "runtime" / "context.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")
    return context, applied
