#!/usr/bin/env python3
"""session_start hook — emits a banner so the operator knows the overlay
is live, and opportunistically refreshes auto-maintained CLAUDE.md
sections (rate-limited so this never spams disk I/O).
"""
import json
import os
import sys

banner = "VibecodeKit v0.11.2 engaged"
auto_writeback = {"ran": False, "reason": "skipped"}

# Best-effort: never let writeback errors block session start.
try:
    repo = os.environ.get("CLAW_PROJECT_ROOT") or os.getcwd()
    here = os.path.dirname(os.path.abspath(__file__))
    # Resolve the vibecodekit Python package across known install layouts.
    # Order: explicit env override → ai-rules overlay → skill bundle dev → none.
    candidates = [
        os.environ.get("VIBECODEKIT_SKILL_PATH"),
        os.path.join(repo, "ai-rules", "vibecodekit", "scripts"),
        os.path.join(here, "..", "..", "..", "skill",
                      "vibecodekit-hybrid-ultra", "scripts"),
        os.path.join(here, "..", "..", "ai-rules",
                      "vibecodekit", "scripts"),
    ]
    for cand in candidates:
        if cand and os.path.isdir(os.path.join(cand, "vibecodekit")):
            sys.path.insert(0, os.path.abspath(cand))
            break
    from vibecodekit.auto_writeback import try_refresh  # type: ignore
    decision = try_refresh(repo)
    auto_writeback = {
        "ran": decision.ran,
        "reason": decision.reason,
        "elapsed_s": round(decision.elapsed_s, 3),
        "sections_updated": list(decision.sections_updated),
    }
except Exception as exc:  # noqa: BLE001
    auto_writeback = {"ran": False, "reason": f"hook_error: {type(exc).__name__}"}

sys.stdout.write(json.dumps({
    "decision": "allow",
    "banner": banner,
    "auto_writeback": auto_writeback,
}))
