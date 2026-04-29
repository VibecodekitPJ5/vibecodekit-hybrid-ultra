# Contributing to vibecodekit-hybrid-ultra

Thanks for your interest in improving VibecodeKit Hybrid Ultra (VCK-HU).
This guide explains the bare-minimum workflow contributors should follow
so PRs land smoothly.

## TL;DR

```bash
git clone https://github.com/N-NewteamPJ369/vibecodekit-hybrid-ultra
cd vibecodekit-hybrid-ultra

# Core (stdlib only, no third-party deps)
PYTHONPATH=./scripts python3 -m pytest tests -q

# With browser extras
pip install -e ".[browser]"
playwright install chromium
PYTHONPATH=./scripts python3 -m pytest tests -q

# Run the conformance audit (must hit 100 %)
VIBECODE_UPDATE_PACKAGE="$(pwd)/update-package" \
  PYTHONPATH=./scripts python3 -m vibecodekit.conformance_audit --threshold 1.0
```

## Project layout (1-minute tour)

| Path | Purpose |
|---|---|
| `scripts/vibecodekit/` | **Core** — stdlib-only; never import third-party deps at module top level. |
| `scripts/vibecodekit/browser/` | Browser daemon (gated behind `[browser]` extra). |
| `scripts/vibecodekit/security_classifier.py` | Regex + optional ONNX + Haiku ensemble (`[ml]` extra). |
| `scripts/vibecodekit/learnings.py`, `team_mode.py` | Per-project JSONL store + team coordination. |
| `update-package/` | The reconciled overlay copied into target projects. |
| `update-package/.claude/commands/` | 26 `/vibe-*` + 14 `/vck-*` slash commands. |
| `update-package/.claude/agents/` | 7 sub-agent profiles (coordinator/scout/builder/qa/security/reviewer/qa-lead). |
| `tests/` | 470+ pytest cases (unit + browser + skill sanity). |

## Quality gates (mandatory)

All PRs MUST pass:

1. `pytest tests -q` — full suite, currently 473 passed / 0 skipped.
2. `python -m vibecodekit.conformance_audit --threshold 1.0` — 85 / 85 probes.
3. `python tools/validate_release_matrix.py --skill . --update ./update-package` —
   L1 + L2 + L3 layouts pass.
4. CI on the PR (`.github/workflows/ci.yml`) — green.

## Coding rules

- **Python ≥ 3.9.**  Type-annotate new code.
- **No third-party deps in core.**  If you need one, gate it behind an
  optional extra (`[browser]`, `[ml]`, …) and self-disable when the dep
  is missing — see `OnnxLayer` for an example.
- **Imports at the top of the file.**  Lazy imports allowed only inside
  functions where the dep is optional.
- **No mutable global state outside `~/.vibecode/` and `.vibecode/`.**
- **Probes must be portable.**  Use `_find_slash_command()` /
  `_candidate_repo_roots()` so they pass in both source checkout and
  L3 installed-project layout.
- **Commit messages** — Conventional Commits style:
  `feat: …`, `fix: …`, `docs: …`, `chore: …`.

## Adding a new `/vck-*` skill

1. Drop the markdown at `update-package/.claude/commands/vck-<name>.md`.
2. Frontmatter MUST include `inspired-by:` (if adapted) and
   `license: MIT (adapted)` plus an attribution paragraph at the bottom.
3. Add the trigger to `manifest.llm.json` and `SKILL.md`.
4. Map intent → slash in `intent_router.py`.
5. Map command → agent role in `subagent_runtime.DEFAULT_COMMAND_AGENT`.
6. Add a sanity test in `tests/test_vck_skills.py`.
7. Bump audit probe count if the skill ships invariants worth probing.

## Reporting issues

Open a GitHub issue with:

- **Reproduction** — minimal steps + Python version + OS.
- **Expected vs actual** — quote the failing assertion / log line.
- **Probe / test name** — if a specific probe or test fails.

## Security disclosure

Email security issues privately to the maintainers listed in `LICENSE`.
Do not file public issues for active vulnerabilities.

## License

By contributing you agree your changes are released under MIT (see
`LICENSE`).  Third-party adaptations stay attributed in
`LICENSE-third-party.md`.

## Attribution

This CONTRIBUTING.md style is adapted from gstack
(© Garry Tan, MIT, commit `675717e3`) — see `LICENSE-third-party.md`.
