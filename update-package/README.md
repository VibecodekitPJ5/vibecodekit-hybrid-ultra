# claw-code-pack (VibecodeKit Hybrid Ultra v0.16.2)

Drop-in overlay for projects that use `claw-code` / Claude Code / Codex.
After extracting into your project root you'll have:

- `.claude/commands/` — **42 slash commands** at v0.16.2: 25 `/vibe-*` + 1 master `/vibe`
  (`/vibe`, `/vibe-scaffold`, `/vibe-ship`, `/vibe-run`, `/vibe-doctor`,
  `/vibe-subagent`, `/vibe-memory`, `/vibe-approval`, `/vibe-task`,
  `/vibe-scan`, `/vibe-vision`, `/vibe-rri`, `/vibe-rri-t`, `/vibe-rri-ux`,
  `/vibe-rri-ui`, …) plus 16 `/vck-*` (`/vck-pipeline`, `/vck-ship`,
  `/vck-review`, `/vck-cso`, `/vck-qa`, …)
- `.claude/agents/` — 7 role cards (coordinator, scout, builder, qa, security, reviewer, qa-lead)
- `.claw/hooks/` — 4 lifecycle hooks (pre/post tool use, pre compact, session start)
- `ai-rules/vibecodekit/` — runtime package + references + templates
- `QUICKSTART.md` — 5-minute onboarding (read this first)
- `CLAUDE.md` — project-overlay notes for Claude Code
- `VERSION` — canonical version string (current: see top-level `VERSION`)

## Install

The update package ships **advisory content only** (slash commands, hooks,
agents, placeholder `ai-rules/` landing-zone). The Python runtime lives in the
**skill bundle** (`vibecodekit-hybrid-ultra-vX.Y.Z-skill.zip`).  Install
both (replace `vX.Y.Z` with the release tag you downloaded):

```bash
# 1. extract the skill bundle somewhere stable on your machine
unzip vibecodekit-hybrid-ultra-vX.Y.Z-skill.zip -d ~/.vibecode

# 2. extract the update package into your project root (slash cmds + hooks + agents)
unzip vibecodekit-hybrid-ultra-vX.Y.Z-update-package.zip -d /path/to/myproject

# 3. run the reconciliation installer from the skill bundle — this copies
#    scripts/references/templates into /path/to/myproject/ai-rules/vibecodekit/
PYTHONPATH=~/.vibecode/vibecodekit-hybrid-ultra/scripts \
  python -m vibecodekit.cli install /path/to/myproject --dry-run

# 4. confirm health
PYTHONPATH=/path/to/myproject/ai-rules/vibecodekit/scripts \
  python -m vibecodekit.cli doctor --root /path/to/myproject
```

Note: `python -m ai-rules.vibecodekit...` is **not** a valid Python module path
(hyphens are not allowed in package names). Always invoke via `vibecodekit.cli`
with `PYTHONPATH` pointing at the scripts directory.

## Release gate

Bản hiện tại trên nhánh `main` (xem `CHANGELOG.md` cho từng release; số
ca pytest tăng theo thời gian — chạy `pytest --collect-only -q | tail`
để xem con số chính xác cho commit của bạn):

- **pytest**: all actionable tests pass (số case tăng theo release; xem `CHANGELOG.md`)
- **conformance self-test**: 87 / 87 internal regression probes pass[^bench] (self-test, not external benchmark; see `BENCHMARKS-METHODOLOGY.md`)
- **fresh-extract self-test**: 87 / 87 probes pass
- **integration tests**: 8 e2e + 3 UX + 6 version-sync

[^bench]: Internal regression gate — chi tiết "87/87" đo cái gì xem `BENCHMARKS-METHODOLOGY.md` (architectural invariants only, không phải benchmark code-quality ngoài như HumanEval / SWE-bench).

Lịch sử các milestone (v0.11.x / v0.15.x / v0.16.x) được giữ trong `CHANGELOG.md`.

See `ai-rules/vibecodekit/SKILL.md`, `ai-rules/vibecodekit/references/00-overview.md`
and `CLAUDE.md` for the complete methodology reference.
