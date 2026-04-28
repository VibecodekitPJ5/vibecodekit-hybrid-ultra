# Third-party attribution

VibecodeKit Hybrid Ultra (VCK-HU) is released under the MIT license (see `LICENSE`). It also incorporates ideas, prompts, and design patterns inspired by the following third-party projects.

---

## gstack — © 2026 Garry Tan, MIT

- Upstream: <https://github.com/garrytan/gstack>
- Reference commit: `675717e3200d8f54b7e179a3425a21bdae33414b` (snapshot 2026-04-28)

### Skills inspired by gstack

The following slash-commands shipped under `update-package/.claude/commands/` were inspired by the matching gstack skill, then **rewritten in Vietnamese-first** for the VCK-HU audience and **integrated** with VCK-HU's permission engine, intent router, and 53-probe audit:

- `/vck-cso` — adapted from `gstack/cso/SKILL.md.tmpl`
- `/vck-review` — adapted from `gstack/review/SKILL.md.tmpl`
- `/vck-qa` and `/vck-qa-only` — adapted from `gstack/qa/SKILL.md.tmpl`
- `/vck-ship` — adapted from `gstack/ship/SKILL.md.tmpl`
- `/vck-investigate` — adapted from `gstack/investigate/SKILL.md.tmpl`
- `/vck-canary` — adapted from `gstack/canary/SKILL.md.tmpl`

Each slash-command file carries a YAML frontmatter `inspired-by` field referencing the upstream skill and commit.

### Browser daemon design pattern

The `scripts/vibecodekit/browser/` Python package borrows the high-level **architecture** of gstack's `browse/` daemon (FastAPI/Bun.serve persistent process + Playwright/CDP + atomic state file with idle-timeout + permission-classified read/write commands + ARIA datamarking envelope). The implementation is a clean-room rewrite in Python; **no source code was copied** from gstack TypeScript.

### ETHOS philosophy layer

`references/40-ethos-vck.md` adapts gstack's ETHOS principles — **Boil the Lake**, **Search Before Building**, **User Sovereignty**, **Build for Yourself** — fused with VCK-HU's existing 3-actor / 8-step VIBECODE-MASTER framing. Original prose has been rewritten in Vietnamese-first; the principles themselves are credited.

---

## License compatibility

gstack is MIT-licensed, which permits redistribution and modification including for commercial purposes, provided attribution and license text are preserved. This file together with the gstack-attributed YAML frontmatters in each ported skill satisfies the attribution requirement.

If you redistribute VCK-HU, you must preserve `LICENSE` (VCK-HU MIT) and this `LICENSE-third-party.md` file.
