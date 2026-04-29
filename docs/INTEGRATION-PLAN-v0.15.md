# Integration Plan v0.15 — "One Pipeline, Zero Dead-Code"

> **Status:** PROPOSAL — chờ user duyệt từng tasks trước khi code.
> **Branch:** chưa tạo (sẽ là `devin/<ts>-vck-pipeline-v015`).
> **Author:** Devin audit cycle — 2026-04-28.
> **Methodology:** VIBECODE-MASTER v5 Step 1 (SCAN) + Step 2 (RRI Architect persona) + Step 4 (BLUEPRINT).

## 1. Mục tiêu

1. **Wire 100 % feature mới (v0.12 → v0.14.1) vào ≥ 1 entry point thực tế** —
   không feature nào chỉ tồn tại trong tài liệu hoặc test.
2. **Đồng bộ 3 sub-pipeline lớn** (project creation / feature dev / code &
   security audit) thành 1 cây quyết định duy nhất, host-agnostic
   (Claude Code, Codex CLI, Cursor, Devin đều chạy được).
3. **Zero dead-code** trong `scripts/vibecodekit/` + `update-package/.claude/`
   + `update-package/.claw/` — mỗi `.py` / `.md` phải có call site
   production hoặc bị xoá.
4. **Invariant guard** (audit probe) ngăn dead-code re-introduce.

## 2. Ground-truth scan (state hiện tại sau v0.14.1)

| Feature | Module | Wired vào runtime / hook? | Wired vào slash command? | Audit probe | Test |
|---|---|---|---|---|---|
| Permission engine | `permission_engine.py` | ✓ pre_tool_use | ✓ /vibe-permission | #1-#10 | ✓ |
| Scaffold | `scaffold_engine.py` | (no hook) | ✓ /vibe-scaffold | #19-#21 | ✓ |
| Deploy orchestrator | `deploy_orchestrator.py` | (no hook) | ✓ /vibe-ship | – | ✓ |
| Browser daemon | `browser/*.py` (9 files) | – | ✓ /vck-qa CLI shells out | #54-#62 | ✓ |
| **`security_classifier`** | `security_classifier.py` | ✓ pre_tool_use **(off-by-default via env)** | **✗ no slash command calls it** | #68-#72 | ✓ |
| **`eval_select`** | `eval_select.py` | **✗ no production call site** | **✗ no slash command** | #73 | ✓ |
| **`learnings`** | `learnings.py` | **✗ no hook** | **✗ /vck-learn doc only mentions it; doesn't auto-call** | #74 | ✓ |
| **`team_mode`** | `team_mode.py` | **✗ no hook** | **✗ /vck-ship doc DOES NOT call `assert_required_gates_run()`** | #75 | ✓ |
| 15 `/vck-*` skills | (markdown only) | – | ✓ via `manifest.llm.json` + `intent_router.py` + `subagent_runtime` | #65-#67 | ✓ |
| GitHub Actions CI | `.github/workflows/ci.yml` | (auto on PR/push) | – | #76 | – |

**4 finding nghiêm trọng — dormant code đang giả vờ "đã tích hợp":**

- **D1.** `team_mode` is **completely orphan** — `/vck-ship.md` không gọi
  `assert_required_gates_run()` ở Bước 1 (Preflight). Doc + audit pass
  nhưng runtime path không bao giờ chạm đến module này.
- **D2.** `eval_select` is **completely orphan** — không command, không hook,
  không CI bước nào dùng. Chỉ tồn tại như standalone tool.
- **D3.** `learnings` is **prose-only integration** — `/vck-learn.md` mô tả
  store nhưng host LLM phải tự gọi `python -m vibecodekit.learnings
  capture` thủ công. `session_start` hook **không** auto-inject (doc
  ghi "đang ở prototype; off by default").
- **D4.** `security_classifier` chỉ active khi user export
  `VIBECODE_SECURITY_CLASSIFIER=1` — trong thực tế **mặc định OFF**, nên
  guard mà ta tự hào ở v0.14.0 chưa thực sự bảo vệ ai.

**Aspirational lies trong docs (cần fix):**

- `USAGE_GUIDE §18` (commit `28c69c9`, vừa thêm) ghi *"`/vck-ship` (orchestrator merge gate) gọi `assert_required_gates_run()`"* — **không đúng** với code thực tế của `vck-ship.md`.
- `README.md` activation cheat sheet ghi `team_mode` "auto-merge into flow via `/vck-ship` gate" — cũng **không đúng**.

## 3. Target architecture v0.15 — 3 pipeline + 1 master command

```
┌────────────────────────────────────────────────────────────────────┐
│  Pipeline A — PROJECT CREATION (greenfield)                        │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ /vibe-scaffold <preset>                                      │  │
│  │   ├─ scaffold files (nguyên bản)                             │  │
│  │   ├─ NEW: seed .vibecode/learnings.jsonl (project scope)     │  │
│  │   ├─ NEW: seed .vibecode/team.json template (commented out)  │  │
│  │   ├─ NEW: seed .vibecode/classifier.env                      │  │
│  │   │     └─ "VIBECODE_SECURITY_CLASSIFIER=1" (commented)      │  │
│  │   └─ NEW: append README banner § "VCK pipeline activated"    │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│  Pipeline B — FEATURE DEVELOPMENT (existing project)               │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ /vibe-scan → /vibe-rri → /vibe-blueprint → /vibe-task        │  │
│  │   → /vibe-run                                                │  │
│  │     ├─ pre_tool_use hook (now classifier ON-by-default       │  │
│  │     │   nếu .vibecode/classifier.env tồn tại HOẶC env var)   │  │
│  │     ├─ /vck-eng-review (lock architecture)                   │  │
│  │     ├─ /vck-learn (auto-capture learning per task done)      │  │
│  │     └─ /vibe-verify (refine boundary)                        │  │
│  │                                                              │  │
│  │ /vck-ship (merge orchestrator)                               │  │
│  │   ├─ Bước 0 NEW: assert_required_gates_run() (team_mode)     │  │
│  │   ├─ Bước 1: preflight                                       │  │
│  │   ├─ Bước 2: test gate (NEW: eval_select trên diff nếu       │  │
│  │   │           tests/touchfiles.json tồn tại; fallback full)  │  │
│  │   ├─ Bước 3: /vck-review (existing)                          │  │
│  │   ├─ Bước 4: /vck-qa-only (existing)                         │  │
│  │   ├─ Bước 5: commit + push                                   │  │
│  │   └─ Bước 6: PR                                              │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│  Pipeline C — CODE & SECURITY AUDIT                                │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ /vck-cso (Chief Security Officer audit)                      │  │
│  │   ├─ existing: OWASP Top 10 + STRIDE checklist               │  │
│  │   └─ NEW: chạy security_classifier.scan_repo() trên          │  │
│  │           toàn bộ file đã commit + flag hits cao tin tưởng   │  │
│  │ /vck-review (adversarial 7-perspective)                      │  │
│  │   └─ NEW: include classifier.scan_diff() trong perspective   │  │
│  │           Security  (vote vào tổng GREEN/YELLOW/RED)         │  │
│  │ /vck-qa (real-browser QA)                                    │  │
│  │   └─ existing: browser daemon đã wired                       │  │
│  │ /vck-investigate (root-cause)                                │  │
│  │   └─ existing                                                │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│  Continuous learning (cross-cut, always-on)                        │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ session_start hook                                           │  │
│  │   └─ NEW: load 10 learnings mới nhất (project ∪ user) →      │  │
│  │           inject vào system prompt addendum                  │  │
│  │ /vck-retro (weekly)                                          │  │
│  │   └─ existing markdown — NEW: thực sự load learnings store   │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

**Master command mới:** `/vck-pipeline` — analog của `/vibe`, dispatcher
free-form prose → pipeline phù hợp (A/B/C). Reuse `intent_router` +
thêm intent `VCK_PIPELINE`.

## 4. Wiring tasks (10 tasks, mỗi task atomic)

### T1 — Wire `team_mode` vào `/vck-ship` (đóng D1)

**File touch:**

- `update-package/.claude/commands/vck-ship.md`
  - Thêm Bước 0 "Team-mode preflight": gọi
    `python -m vibecodekit.team_mode check` → exit-code-driven gate.
- `scripts/vibecodekit/team_mode.py`
  - Thêm CLI subcommand `check` đọc `.vibecode/team.json`, chạy
    `assert_required_gates_run()` từ session ledger
    (`.vibecode/session_ledger.jsonl` — tạo mới nếu cần).
- `scripts/vibecodekit/cli.py`
  - Add `team` subcommand (`vibe team init|check|list`).
- Tests: `tests/test_team_mode_cli.py` (~6 cases).

**Backwards compat:** repo không có `.vibecode/team.json` → no-op (exit 0).

### T2 — Wire `eval_select` vào `/vck-ship` test gate + CI (đóng D2)

**File touch:**

- `update-package/.claude/commands/vck-ship.md` Bước 2 (Test gate):
  - Nếu `tests/touchfiles.json` tồn tại → chạy
    `python -m vibecodekit.eval_select --base <base> --map ...
    --json` → lấy `selected[]` chạy pytest selective.
  - Fallback full suite nếu file không có.
- `.github/workflows/ci.yml`:
  - Thêm step "selective tests on PR" (chỉ trên `pull_request`, không
    trên `push to main`):
    ```yaml
    - name: Selective tests (eval_select)
      if: github.event_name == 'pull_request' && hashFiles('tests/touchfiles.json') != ''
      run: python -m vibecodekit.eval_select --base origin/${{ github.base_ref }} --map tests/touchfiles.json --json | tee selected.json
    ```
  - Sau đó pytest đọc `selected.json` (nếu có) để chỉ chạy subset; full
    suite vẫn chạy trên `push to main`.
- `tests/touchfiles.json` (new) — seed với mapping core hiện tại.
- Tests: `tests/test_eval_select_cli_integration.py` (~4 cases).

### T3 — Wire `learnings` vào `session_start` + `/vck-learn` thực sự append (đóng D3)

**File touch:**

- `update-package/.claw/hooks/session_start.py`:
  - Thêm block:
    ```python
    if os.environ.get("VIBECODE_LEARNINGS_INJECT", "1") == "1":
        try:
            from vibecodekit.learnings import recent_for_prompt
            addendum = recent_for_prompt(limit=10, scopes=("project","user"))
            if addendum:
                print(json.dumps({"hook":"session_start","addendum":addendum}))
        except Exception:
            pass
    ```
- `scripts/vibecodekit/learnings.py`:
  - Thêm helper `recent_for_prompt(limit, scopes)` → format markdown
    addendum.
- `update-package/.claude/commands/vck-learn.md`:
  - Sửa "Integration" section: bỏ ghi chú "đang ở prototype; off by
    default" → ghi đúng cách bật `VIBECODE_LEARNINGS_INJECT=0` để tắt.
- `scripts/vibecodekit/cli.py`:
  - Add `learn` subcommand pass-through.
- Tests: `tests/test_session_start_learnings_inject.py` (~5 cases —
  inject + skip when env=0 + cap at limit + scope filter +
  graceful-empty).

### T4 — Wire `security_classifier` vào `/vck-review` + `/vck-cso` (đóng D4 — auto-on, opt-out)

**File touch:**

- `update-package/.claude/commands/vck-review.md`:
  - Bổ sung perspective "Security" hiện tại: chạy
    `python -m vibecodekit.security_classifier --scan-diff <base>` →
    output JSON; merge vào tổng kết review.
- `update-package/.claude/commands/vck-cso.md`:
  - Bổ sung Step "regex pre-scan": chạy
    `python -m vibecodekit.security_classifier --scan-paths
    <changed-files>` để bổ sung OWASP/STRIDE manual checklist.
- `scripts/vibecodekit/security_classifier.py`:
  - CLI `--scan-diff <base>` (mới).
  - CLI `--scan-paths <p1> <p2> ...` (mới).
  - Output JSON ổn định.
- `update-package/.claw/hooks/pre_tool_use.py`:
  - **Đổi default:** nếu `.vibecode/classifier.env` tồn tại HOẶC env
    var được export → bật. Fallback: vẫn off (giữ backward compat).
- Tests: `tests/test_classifier_cli_scan.py` (~6 cases).

### T5 — Wire scaffold engine seed các config mới (mở Pipeline A)

**File touch:**

- `scripts/vibecodekit/scaffold_engine.py`:
  - Mở rộng `apply_preset()`: sau khi copy preset, gọi `_seed_vck_pipeline(dst)`:
    - Tạo `.vibecode/learnings.jsonl` (file rỗng).
    - Tạo `.vibecode/team.json.example` với schema commented.
    - Tạo `.vibecode/classifier.env.example` với env hướng dẫn.
    - Append vào `README.md` bullet "## Pipeline VCK đã sẵn sàng".
- Tests: `tests/test_scaffold_seeds_vck.py` (~4 cases).

### T6 — `/vck-pipeline` master command (mở 1 cửa cho tất cả)

**File touch:**

- `update-package/.claude/commands/vck-pipeline.md` (NEW):
  - Frontmatter: triggers ["pipeline","đầy đủ","full check","go through pipeline"].
  - Body: dispatch theo prose của user → pipeline A/B/C.
- `scripts/vibecodekit/intent_router.py`:
  - Thêm intent `VCK_PIPELINE`.
- `manifest.llm.json` + `SKILL.md`: thêm `vck-pipeline`.
- `update-package/.claw.json` + `update-package/manifest.llm.json`:
  cùng cập nhật.
- Tests: `tests/test_vck_pipeline_intent.py` (~3 cases).

### T7 — Dead-code probe (#78) — invariant guard

**File touch:**

- `scripts/vibecodekit/conformance_audit.py`:
  - Thêm probe `78_no_orphan_module`:
    - Walk mọi `scripts/vibecodekit/*.py` (loại trừ `__init__`,
      `__main__`, helper internal).
    - Mỗi module phải có ≥ 1 import từ:
      - `update-package/.claw/hooks/*.py` (hook), HOẶC
      - `update-package/.claude/commands/*.md` (slash), HOẶC
      - `scripts/vibecodekit/cli.py` (subcommand), HOẶC
      - `tests/**/*.py` (chỉ nếu module có CLI `__main__` block).
    - Allowlist nội bộ (e.g. helper utility) ghi rõ trong
      `scripts/vibecodekit/_audit_allowlist.json`.
  - Probe FAIL liệt kê module orphan + lý do.
- Tests: `tests/test_audit_probe_78_no_orphan.py` (~3 cases).

### T8 — Sửa aspirational docs (đóng các "lời hứa giả")

**File touch:**

- `USAGE_GUIDE.md §18`:
  - Sửa bullet `team_mode` → "Sau v0.15, /vck-ship sẽ thực sự chạy assert_required_gates_run() ở Bước 0".
  - **Hoặc** chỉ sửa khi T1 đã merge — diễn đạt theo state thực.
- `README.md` activation cheat sheet — đồng bộ.
- `docs/AUDIT-v0.14.0.md` — ghi note "v0.14.1 audit phát hiện thêm
  D1-D4 dormant; được fix trong v0.15 — xem
  `docs/INTEGRATION-PLAN-v0.15.md`".

### T9 — Audit probes mới #79-#82 cho integration invariants

| Probe | Kiểm |
|---|---|
| #79 | `/vck-ship.md` reference `team_mode` |
| #80 | `pre_tool_use.py` reference `security_classifier` (ĐÃ có, giữ) |
| #81 | `session_start.py` reference `learnings` |
| #82 | `scaffold_engine.py` reference `_seed_vck_pipeline` |

Mỗi probe FAIL → audit gate sập → CI sập → không merge được.

### T10 — Release matrix + version bump

- `VERSION` 0.14.1 → 0.15.0
- `pyproject.toml`, `SKILL.md`, `manifest.llm.json`,
  `assets/plugin-manifest.json`, `update-package/.claw.json`,
  `update-package/VERSION`, `update-package/manifest.llm.json` ←
  đồng bộ.
- `CHANGELOG.md` mục `[0.15.0] — Unified pipeline + zero dead-code`:
  - Section `### Added`: T1, T2, T3, T4, T5, T6, T7, T9.
  - Section `### Changed`: T8 (docs sync).
  - Section `### Removed`: bất kỳ skill / file orphan nào (chưa rõ — sẽ
    confirm sau khi T7 chạy).

## 5. Verification plan

```
1. pytest                        : ≥ 555 passed (536 + ~19 cho T1-T7)
2. conformance audit             : 81/81 @ 100 % (77 + 4 từ T9)
3. release matrix L1+L2+L3       : PASS
4. CI 3.9 / 3.11 / 3.12          : ✓
5. Smoke test thủ công           :
   - /vibe-scaffold next-saas demo-app  → check .vibecode/* seeded
   - cd demo-app && /vck-ship           → team_mode + eval_select fire
   - touch a.py && /vck-cso             → classifier scan in output
   - VIBECODE_LEARNINGS_INJECT=1 + open new session → addendum xuất hiện
6. Probe #78 chạy local          : 0 orphan
```

## 6. Risk + mitigation

| Risk | Mitigation |
|---|---|
| Bật classifier mặc định có thể block flow cũ | T4 chỉ bật khi `.vibecode/classifier.env` HOẶC env var; mặc định flow legacy KHÔNG đổi |
| `session_start` inject làm context window phình | Cap ở `limit=10` + `VIBECODE_LEARNINGS_INJECT=0` để tắt |
| `eval_select` chọn sai → bỏ sót regression | Fallback full-suite trên `push to main`; PR vẫn full nếu `tests/touchfiles.json` không có |
| `/vck-pipeline` master command conflict với `/vibe` | Phân biệt rõ trong frontmatter description; intent_router ưu tiên match prefix nguyên văn |
| Probe #78 false-positive cho helper utility | `_audit_allowlist.json` cho phép user pin |
| Big-bang merge phá v0.14.1 đang stable | Chia 4 PR (xem §7) |

## 7. Rollout — chia 4 PR

| PR | Scope | Risk | Tests delta |
|---|---|---|---|
| **PR-A** v0.15.0-alpha | T1 + T2 (gate wiring) + T8 docs sync | thấp (chỉ thêm gate, không thay default) | +10 |
| **PR-B** v0.15.0-beta | T3 + T4 (auto-on with opt-out) | trung (đổi default behaviour) | +11 |
| **PR-C** v0.15.0 | T5 + T6 (scaffolding + master command) | thấp (greenfield only) | +7 |
| **PR-D** v0.15.1 | T7 + T9 (invariant guards) + T10 (version bump + cleanup) | thấp (audit-only) | +3 |

User có thể **veto từng PR** mà không phá flow v0.14.1 đang chạy. Mỗi PR
đều phải qua 4 gates (pytest + audit + release-matrix + Devin Review).

## 8. RRI Architect persona — phản biện 5 câu

1. **Cynic:** "T6 master command có overlap với `/vibe` không?" → Có,
   nhưng `/vibe` là dispatch generic 25 lệnh `/vibe-*`, `/vck-pipeline`
   là dispatch giữa **3 pipeline lớn** (A/B/C). Different layer.
2. **Skeptic:** "Auto-bật classifier ở T4 sẽ break repo cũ?" → Mitigation:
   chỉ bật khi `.vibecode/classifier.env` tồn tại; legacy repo không có
   file → behaviour không đổi.
3. **Trickster:** "Đường vòng nào để tắt session_start inject?" →
   `VIBECODE_LEARNINGS_INJECT=0` HOẶC xoá `.vibecode/learnings.jsonl`.
4. **Auditor:** "Có dấu vết telemetry gì cho user check pipeline thực
   sự chạy?" → Mỗi step ghi vào `.vibecode/session_ledger.jsonl`
   (T1 đã tạo); `/vibe-dashboard` đọc ra HTML.
5. **Lead:** "ETA hợp lý?" → 4 PR × ~2-3 ngày work = 8-12 ngày tổng.
   Có thể parallelize PR-C (independent) sau khi PR-A merge.

## 9. Open questions cho user (cần trả lời trước khi tôi code)

1. **Auto-on classifier** ở T4 (đổi default):
   - (a) Auto-on khi `.vibecode/classifier.env` HOẶC env var tồn tại
     (đề xuất — backward compat).
   - (b) Auto-on luôn (mạnh tay hơn, có thể break legacy).
   - (c) Vẫn opt-in tuyệt đối qua env var (giữ nguyên v0.14.1).
2. **`session_start` inject learnings** (T3):
   - (a) Default ON (`VIBECODE_LEARNINGS_INJECT=1` mặc định) — đề xuất.
   - (b) Default OFF, user phải bật.
3. **`eval_select` ở CI** (T2):
   - (a) Bật trên PR-only, full trên `push to main` — đề xuất.
   - (b) Bật cả 2 (tăng tốc CI thêm).
   - (c) Không bật ở CI, chỉ ở local `/vck-ship`.
4. **Chia 4 PR vs 1 PR lớn** (§7):
   - (a) 4 PR — đề xuất.
   - (b) 1 PR đơn (gọn cho user review nhưng risk cao).
5. **Probe #78 allowlist** — module nào bạn cố ý muốn giữ orphan?
   (e.g. `vn_faker` chỉ là utility cho test data, có thể allowlist).

## 10. Quyết định (chờ user)

> ☐ Approve plan, bắt đầu PR-A (T1 + T2 + T8).
> ☐ Approve có sửa — câu trả lời 5 câu hỏi §9.
> ☐ Reject — yêu cầu plan khác.
> ☐ Hỏi thêm trước khi quyết.
