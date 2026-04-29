---
name: vck-pipeline
description: Master router — type free-form prose to dispatch to one of the 3 VCK-HU pipelines (A. PROJECT CREATION / B. FEATURE DEV / C. CODE & SECURITY)
version: 0.15.5
allowed-tools: [Bash, Read]
agent: coordinator
inspired-by: ../vibe.md
license: MIT (adapted)
---

# /vck-pipeline

Single-prompt master router — analog of `/vibe` but scoped to the
3 **VCK-HU** pipelines that ship in v0.15.0-alpha:

| Code | Pipeline | Runs |
|---|---|---|
| **A** | PROJECT CREATION | `/vibe-scaffold` (auto-seeds `.vibecode/` per T5) → `/vibe-blueprint` |
| **B** | FEATURE DEV | `/vibe-run` (security classifier auto-on per T4) → `/vck-ship` (team-mode preflight + eval_select) |
| **C** | CODE & SECURITY | `/vck-cso` (OWASP + STRIDE) → `/vck-review` (multi-perspective adversarial) |

## Usage

```bash
# Route prose → pipeline + canonical command sequence
python -m vibecodekit.pipeline_router route "làm cho tôi shop online bán cà phê"
# → pipeline: A — PROJECT CREATION
#   commands: ["/vibe-scaffold", "/vibe-blueprint"]

# List the 3 pipelines
python -m vibecodekit.pipeline_router list
```

## Programmatic API

```python
from vibecodekit.pipeline_router import PipelineRouter
r = PipelineRouter()
d = r.route("audit code review for security")
# d.pipeline == "C"
# d.commands == ("/vck-cso", "/vck-review")
# d.confidence == 1.0
```

## How it routes

The router applies a small VN + EN keyword bank — same shape as
`/vibe` but **only 3 buckets** so the dispatch is unambiguous:

1. **Score each pipeline** by counting how many of its keywords appear
   in the normalised prose (lowercased + whitespace collapsed).
2. **Confidence = `min(1.0, hits / 2)`** so a single very-specific
   match ("owasp", "scaffold") is already high-confidence.
3. **Below 0.5** the router asks the operator to clarify and reports
   the top-2 candidate codes, instead of guessing.

The keyword bank is intentionally short.  Adding a keyword requires a
matching test in `tests/test_pipeline_router.py`.

## Examples

| Prose | Pipeline | Commands |
|---|---|---|
| `"làm cho tôi shop online"` | **A** | `/vibe-scaffold → /vibe-blueprint` |
| `"thêm tính năng login"` | **B** | `/vibe-run → /vck-ship` |
| `"audit code security OWASP"` | **C** | `/vck-cso → /vck-review` |
| `"scaffold landing page"` | **A** | `/vibe-scaffold → /vibe-blueprint` |
| `"sửa lỗi peer-deps"` | **B** | `/vibe-run → /vck-ship` |
| `"kiểm tra bảo mật"` | **C** | `/vck-cso → /vck-review` |

## Why this exists

PR-A wired `team_mode` + `eval_select` into `/vck-ship`.  PR-B made
the security classifier and learnings auto-on by default.  But to a
new operator typing *"audit code"* into Claude Code, this still meant
discovering 5 different `/vck-*` and `/vibe-*` commands.

`/vck-pipeline` is the **one entrypoint that ties all of v0.15.0-alpha
together**.  It does not replace `/vibe` — it complements it for
operators who want to think in pipelines instead of individual
commands.

## References

- `docs/INTEGRATION-PLAN-v0.15.md` §3 — master plan (T6)
- `update-package/.claude/commands/vibe.md` — analog router (`/vibe`)
- `scripts/vibecodekit/pipeline_router.py` — runtime backing this command

---

Adapted from VibecodeKit's `/vibe` master router (clean-room
rewrite, no upstream code copied).  Scoped specifically to the three
VCK-HU pipelines that ship in v0.15.0.  Xem
`LICENSE-third-party.md`.
