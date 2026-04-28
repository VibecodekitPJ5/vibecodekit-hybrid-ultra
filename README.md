# VibecodeKit Hybrid Ultra

> **Current release:** [v0.11.4.1](https://github.com/ykjpalbubp/vibecodekit-hybrid-ultra/releases/tag/v0.11.4.1)
> A defensive, audit-driven runtime + skill bundle for AI-assisted
> coding workflows.  Ships with VIBECODE-MASTER v5 methodology,
> RRI-T / RRI-UI / RRI-UX question banks, a permission engine,
> a scaffold engine, and a 53-probe self-audit gate.

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
[Releases](https://github.com/ykjpalbubp/vibecodekit-hybrid-ultra/releases/latest):

```bash
# Skill bundle (full runtime + tests + docs)
curl -L https://github.com/ykjpalbubp/vibecodekit-hybrid-ultra/releases/download/v0.11.4.1/vibecodekit-hybrid-ultra-v0.11.4.1-skill.zip -o skill.zip
unzip skill.zip -d ~/.claude/skills/vibecodekit-hybrid-ultra
```

### Option 2 — install update package into an existing project

```bash
curl -L https://github.com/ykjpalbubp/vibecodekit-hybrid-ultra/releases/download/v0.11.4.1/vibecodekit-hybrid-ultra-v0.11.4.1-update-package.zip -o update.zip
unzip update.zip -d /path/to/your/project/
```

The update package is what `python -m vibecodekit.cli install <dst>`
copies under the hood (251 files into `.claude/`, `.claw.json`,
docs, etc.).

---

## Develop locally

```bash
git clone https://github.com/ykjpalbubp/vibecodekit-hybrid-ultra.git
cd vibecodekit-hybrid-ultra

# Run the canonical release gate
VIBECODE_UPDATE_PACKAGE="$(pwd)/update-package" \
PYTHONPATH=./scripts \
python3 -m pytest tests -q

python3 tools/validate_release_matrix.py \
    --skill   "$(pwd)" \
    --update  "$(pwd)/update-package"
```

Expected gate output:

```
pytest                            : 367 passed, 15 skipped
audit (×any)                      : 53/53 met=True
validate_release_matrix (default) : PASS
```

(Under `root`, pytest reports `366 passed, 16 skipped` — the
`test_install_into_readonly_dir` test is intentionally
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

Not yet specified.  Treat as "all rights reserved" by default until
a `LICENSE` file is added.  Open an issue if you need a specific
license added.

---

## Status

| Gate | Result |
|---|---|
| pytest (367 cases) | PASS |
| audit (53 probes) | 53/53 met=True |
| validate_release_matrix (default) | PASS in 2.1s |
| All 170 Cf codepoints × `rm -rf /` bypass | blocked |

See `CHANGELOG.md` for full history and `v0.11.4.1-refine-report.md`
on the latest release for stress-dipdive results.
