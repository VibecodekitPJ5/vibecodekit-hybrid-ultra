# VibecodeKit Hybrid Ultra

> **Current release:** v0.16.2 ([CHANGELOG](CHANGELOG.md))
> A defensive, audit-driven runtime + skill bundle for AI-assisted
> coding workflows.  42 commands (25 `/vibe-*` + 1 `/vibe` + 16 `/vck-*`) ·
> 7 sub-agent roles · 33 hook events · 6-layer permission pipeline ·
> 3-tier persistent memory · MCP integration · VIBECODE-MASTER v5
> methodology · RRI-T / RRI-UI / RRI-UX question banks · Python-pure
> browser daemon · scaffold engine (10 presets × 3 stacks).

> **License:** MIT — see [`LICENSE`](LICENSE) and the third-party
> attribution manifest [`LICENSE-third-party.md`](LICENSE-third-party.md).

## Quick demo (< 2 seconds, zero network)

```bash
git clone https://github.com/VibecodekitPJ3/vibecodekit-hybrid-ultra.git
cd vibecodekit-hybrid-ultra
PYTHONPATH=./scripts python -m vibecodekit.cli demo
```

Runs 6 steps offline: doctor health-check, permission engine (classify 5
commands), conformance audit (87 probes), scaffold preview, intent router,
and MCP selfcheck.  See [`examples/`](examples/) for standalone scripts.

## Skills inspired by gstack

v0.15.0 closes the **One Pipeline, Zero Dead-Code** rollout:
team-mode + eval_select wired into `/vck-ship`, security classifier +
learnings inject auto-on, scaffold seeds for `.vibecode/`, the master
`/vck-pipeline` router, and a new audit probe that fails CI if any
module under `scripts/vibecodekit/` lacks a production call site —
lifting the internal conformance self-test to 87 probes (was 85 in v0.15.0; see [`BENCHMARKS-METHODOLOGY.md`](BENCHMARKS-METHODOLOGY.md) for what this measures).
v0.14.0 added eight `/vck-*` commands (plan reviews + polish), an
optional `security_classifier` ensemble (`[ml]` extra), per-project
learnings / team-mode coordination stores, GitHub Actions CI, and
`CONTRIBUTING.md`.
v0.12.0 introduced seven `/vck-*` slash commands and a Python browser
daemon adapted — with attribution — from
[gstack](https://github.com/garrytan/gstack) (© Garry Tan, MIT,
commit `675717e3`):

- `/vck-cso` — Chief Security Officer audit (OWASP Top 10 + STRIDE).
- `/vck-review` — 7-perspective adversarial review (architect / security / perf / a11y / ux / dx / risk).
- `/vck-qa`, `/vck-qa-only` — real-browser QA checklist VN-12.
- `/vck-ship` — atomic test → review → qa → commit → push → PR.
- `/vck-investigate` — NO-FIX-WITHOUT-INVESTIGATION root-cause flow.
- `/vck-canary` — 30-minute post-deploy monitor.

The browser daemon is a **clean-room Python reimplementation** of
gstack's persistent-daemon architecture (atomic state file + idle
timeout + permission-classified commands + ARIA datamarking + URL
blocklist).  It ships stdlib-only for the core; Playwright + FastAPI
are gated behind the `[browser]` extra:

```bash
pip install "vibecodekit-hybrid-ultra[browser]"
playwright install chromium
```

See [`LICENSE-third-party.md`](LICENSE-third-party.md) for the full
per-artefact attribution table and
[`references/40-ethos-vck.md`](references/40-ethos-vck.md) for the
ETHOS adaptation.

### Activation cheat sheet (v0.15.0-alpha)

| Module | Auto-merged into VCK-HU flow? | Activate by |
|---|---|---|
| `security_classifier` | ✓ via `pre_tool_use` hook (auto-on default since v0.15.0-alpha PR-B) | always on; opt-out `VIBECODE_SECURITY_CLASSIFIER=0` |
| `eval_select` | ✓ via `/vck-ship` Bước 2 + CI preview | drop `tests/touchfiles.json` |
| `learnings` | ✓ via `session_start` hook (auto-inject 10 latest, PR-B) + `/vck-learn` + `/vck-retro` | always on; opt-out `VIBECODE_LEARNINGS_INJECT=0` |
| `team_mode` + `session_ledger` | ✓ via `/vck-ship` Bước 0 (gate enforcement) | `python -m vibecodekit.team_mode init …` |
| browser daemon | ✓ via `/vck-qa` skill | `pip install -e ".[browser]"` |
| 16 `/vck-*` slash commands | ✓ via manifest + intent_router | type `/vck-<name>` in host |
| GitHub Actions CI | ✓ on every PR/push (3.9 / 3.11 / 3.12) | always on |

Full walkthrough: [`USAGE_GUIDE.md` §18](USAGE_GUIDE.md#18-activation-cheat-sheet--gstack-port-modules-v0120v0150).

---

## Layout

```
vibecodekit-hybrid-ultra/
├── SKILL.md                ← Claude/Cursor skill manifest (entry point)
├── USAGE_GUIDE.md          ← User-facing walkthrough
├── QUICKSTART.md           ← 5-minute setup
├── CHANGELOG.md            ← Release history
├── VERSION                 ← Canonical version (single source of truth)
├── manifest.llm.json       ← LLM-readable manifest
│
├── assets/                 ← Plugin manifest, RRI question banks, scaffold templates
├── scripts/                ← Python runtime (vibecodekit/ package)
│   └── vibecodekit/
│       ├── cli.py
│       ├── permission_engine.py    ← classify_cmd, _normalise_unicode (Cf strip)
│       ├── install_manifest.py     ← fcntl-locked installer
│       ├── methodology.py          ← RRI loaders + VIBECODE-MASTER v5
│       ├── scaffold_engine.py      ← 10 presets × 3 stacks
│       ├── doctor.py
│       └── audit.py
│
├── tests/                  ← 367 pytest cases (root: 366 + 1 skipped)
├── tools/                  ← validate_release_matrix.py + helpers
├── references/             ← VIBECODE-MASTER v5, RRI methodology docs
├── runtime/                ← Runtime data (RRI cycles, etc.)
│
└── update-package/         ← Drop-in payload that gets copied into a user project
    ├── README.md
    ├── USAGE_GUIDE.md
    ├── CLAUDE.md
    ├── VERSION
    ├── .claw.json
    └── .claude/            ← Claude config (commands, hooks)
```

---

## Install (for end users)

### Option 1 — drop the skill into Claude Code / Cursor

Download the latest skill bundle from
[Releases](https://github.com/VibecodekitPJ3/vibecodekit-hybrid-ultra/releases/latest):

```bash
# Skill bundle (full runtime + tests + docs)
# Replace vX.Y.Z with the latest release tag (see /releases page).
curl -L https://github.com/VibecodekitPJ3/vibecodekit-hybrid-ultra/releases/download/vX.Y.Z/vibecodekit-hybrid-ultra-vX.Y.Z-skill.zip -o skill.zip
unzip skill.zip -d ~/.claude/skills/vibecodekit-hybrid-ultra
```

### Option 2 — install update package into an existing project

```bash
# Replace vX.Y.Z with the latest release tag (see /releases page).
curl -L https://github.com/VibecodekitPJ3/vibecodekit-hybrid-ultra/releases/download/vX.Y.Z/vibecodekit-hybrid-ultra-vX.Y.Z-update-package.zip -o update.zip
unzip update.zip -d /path/to/your/project/
```

The update package is what `python -m vibecodekit.cli install <dst>`
copies under the hood (251 files into `.claude/`, `.claw.json`,
docs, etc.).

---

## Develop locally

```bash
git clone https://github.com/VibecodekitPJ3/vibecodekit-hybrid-ultra.git
cd vibecodekit-hybrid-ultra

# Run the canonical release gate
VIBECODE_UPDATE_PACKAGE="$(pwd)/update-package" \
PYTHONPATH=./scripts \
python3 -m pytest tests -q

python3 tools/validate_release_matrix.py \
    --skill   "$(pwd)" \
    --update  "$(pwd)/update-package"
```

Expected gate output (concrete count grows with each release — the
important invariant is that pytest exits 0 with no failures and the
internal conformance self-test reports all probes passing).  Số liệu
tham khảo dưới đây ứng với commit hiện tại trên nhánh `main` (xem
[`CHANGELOG.md`](CHANGELOG.md) cho từng release):

```
pytest                            : <N> passed                # at current main (see CHANGELOG.md)
audit (×any)                      : 87/87 met=True[^bench]    # at current main (internal self-test)
validate_release_matrix (default) : PASS
```

[^bench]: Internal regression gate — see [BENCHMARKS-METHODOLOGY.md](BENCHMARKS-METHODOLOGY.md) for what the 87/87 number actually measures (architectural invariants only, not external code-quality benchmarks).

Để lấy số chính xác cho bản đang ở local, chạy:

```bash
cat VERSION                                                  # ví dụ: 0.16.2
VIBECODE_UPDATE_PACKAGE="$(pwd)/update-package" \
  PYTHONPATH=./scripts python3 -m pytest tests -q | tail -1  # số case pytest
PYTHONPATH=./scripts python3 -m vibecodekit.conformance_audit \
    --threshold 1.0 | head -1                                # ví dụ: parity: 100.00% (87/87, threshold 100%)
```

(Under `root`, the `test_install_into_readonly_dir` test is intentionally
`skipif(geteuid() == 0)` because root bypasses POSIX DAC and the
sibling file-where-dir test already covers the surface.)

---

## Release artifacts

Each tagged release ships three artifacts:

| Artifact | Description |
|---|---|
| `vibecodekit-hybrid-ultra-vX.Y.Z-skill.zip` | Full skill bundle (drop into `~/.claude/skills/`) |
| `vibecodekit-hybrid-ultra-vX.Y.Z-update-package.zip` | Drop-in payload for existing projects |
| `vX.Y.Z-refine-report.md` | Stress-dipdive / refine notes for the release |

The canonical CHANGELOG is in [`CHANGELOG.md`](CHANGELOG.md).

---

## Methodology

This repo implements two layered methodologies:

* **VIBECODE-MASTER v5** — 8-phase release cycle:
  SCAN → RRI → VISION → BLUEPRINT → TASK GRAPH → BUILD → VERIFY → REFINE.
  See `references/VIBECODE-MASTER-v5.txt`.

* **RRI (Reverse Requirements Interview)** — three flavours:
  * RRI-T (Testing) — 7 dimensions × 8 stress axes
  * RRI-UI — UI-state coverage matrix
  * RRI-UX — UX-flow coverage matrix

  See `references/RRI-*_METHODOLOGY.docx` and `runtime/rri/`.

Question banks live in `assets/rri-question-bank.json`
(schema 1.2.0, 12 project-type buckets, 5 personas × 3 modes).

---

## License

MIT (with attribution paragraph for the gstack-derived `/vck-*` slash
commands).  See [`LICENSE`](LICENSE) for the canonical text and
[`LICENSE-third-party.md`](LICENSE-third-party.md) for the inspiration
/ rewrite-and-integration credit on the gstack → `/vck-*` derivation.

---

## Quality assurance

Số ca pytest và số probe lớn dần theo từng release; bảng dưới đây
phản ánh trạng thái **tại nhánh `main` hiện tại** (xem
[`CHANGELOG.md`](CHANGELOG.md) cho lịch sử số liệu theo từng version,
và [`BENCHMARKS-METHODOLOGY.md`](BENCHMARKS-METHODOLOGY.md) để biết
"87/87" thực sự đo cái gì — không phải benchmark chất lượng ngoài).

| Gate | Result | What it measures |
|---|---|---|
| pytest (xem `pytest --collect-only -q \| tail`) | PASS | Unit + integration correctness |
| conformance self-test | 87/87 met=True[^bench] | Internal regression invariants ([details](BENCHMARKS-METHODOLOGY.md)) |
| validate_release_matrix (default) | PASS | Layout integrity across 3 deploy modes |
| All 170 Cf codepoints × `rm -rf /` bypass | blocked | Permission engine coverage |

See `CHANGELOG.md` for full version history and the per-release
`*-refine-report.md` artifacts (kept under `docs/historical/` for
releases more than two minors old).
