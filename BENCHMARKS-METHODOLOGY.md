# Benchmarks & Methodology

> **TL;DR:** The "87/87 @ 100 %" number in our docs is a
> **self-conformance regression test**, not an external quality benchmark.
> It proves the runtime has not regressed since the last release — it
> does **not** measure code-generation quality, bug-fix rate, or
> reasoning depth.

---

## 1. What `conformance_audit` actually measures

`conformance_audit` (invoked via `/vibe-audit` or the CLI) runs 87
internal probes (at v0.16.2; count grows with each release) that check
**architectural invariants**:

| Category | Example probes | What it proves |
|---|---|---|
| Module wiring | "Does `intent_router` map all 42 slash commands?" | No dead-code or orphan modules |
| Hook coverage | "Are all 33 lifecycle events in `SUPPORTED_EVENTS`?" | Hook system is complete |
| ACL profiles | "Does `qa` role have `can_mutate=False`?" | Permission model intact |
| Frontmatter integrity | "Does every `/vck-*` command have `inspired-by:`?" | Attribution metadata present |
| Methodology gates | "Does RRI question bank cover 5 personas x 3 modes?" | Methodology coverage |
| Security hardening | "Is Unicode Cf-class normalisation applied?" | Permission bypass classes closed |

Passing 87/87 means: **"the runtime has not regressed against its own
specification."**

## 2. What it does NOT measure

| Dimension | Measured by | Status in VCK-HU |
|---|---|---|
| Code generation quality | HumanEval, MBPP, BigCodeBench | Not yet benchmarked |
| Real-world bug-fix rate | SWE-bench Lite, SWE-bench Verified | Not yet benchmarked |
| Reasoning depth | ARC, GPQA, MATH | Not yet benchmarked |
| Agent autonomy | METR HCAST, AgentBench, WebArena | Not yet benchmarked |
| End-user satisfaction | A/B test, NPS, task-completion rate | Not yet benchmarked |

**Important:** "100 % parity" in our docs refers to parity with the
project's own internal specification ("Giai phau mot Agentic Operating
System"), **not** parity with any external model or tool.

## 3. How to read our quality claims

| Claim in docs | What it actually means |
|---|---|
| "87/87 probes pass" | All internal regression invariants hold |
| "100 % parity" | Runtime matches its own architectural spec |
| "passes conformance audit" | Self-test gate; not an external benchmark |
| "588 pytest cases pass" | Unit + integration tests pass (code correctness) |
| "release-matrix L1+L2+L3 PASS" | Layout validation across 3 deployment modes |

## 4. Intent router accuracy (set-inclusion, N=104)

`tests/test_intent_router_golden.py` chạy `IntentRouter().classify()`
trên dataset có nhãn ở `tests/fixtures/intent_router_golden.jsonl`
(40 EN clear + 44 VI clear + 20 edge / ambiguous, total **104**
entries) và đo:

| Metric | Định nghĩa | Giá trị hiện tại | Gate |
|---|---|---|---|
| `set_inclusion_accuracy` | `mean(_entry_passes(expected, actual))` — `expected ⊆ actual` khi `expected` non-empty; **`actual == ∅`** khi `expected == ∅` (clarification expected) | **98.1 %** (102/104 ở v0.16.2 sau fix clarification-trigger override) | **≥ 75 %** (hard, không hạ ngưỡng nếu tụt) |
| `exact_match_accuracy` | `mean(expected == actual)` — báo cáo only | **88.5 %** (92/104) | ≥ 50 % (cảnh báo super set quá rộng) |
| Per-locale (EN, VI) | set-inclusion riêng từng locale | EN ≥ 75 %, VI ≥ 75 % | đảm bảo không lệch sang một locale |

> **Lịch sử**:
>
> * Baseline trước fix vacuous-pass (Devin Review báo trên PR #28) là
>   98.1 % (102/104).  Bug: 10 entry tag `ambiguous` có
>   `expected_intents = []` luôn vacuously pass
>   `expected.issubset(actual)` (empty set là subset của mọi set) →
>   router có thể trả intent thay vì Clarification mà vẫn pass.  Sau
>   fix #29, 1 entry mới hiện hình thành miss
>   (`"không biết làm sao luôn á"` → router trả `{BUILD}` chỉ vì
>   `"làm"` nằm trong BUILD trigger list) → 97.1 % (101/104).
> * Sau follow-up clarification-trigger override (PR sau #31): thêm
>   `_CLARIFICATION_TRIGGERS` (VN: `"không biết"`, `"luôn á"`, `"làm
>   sao"`, `"bí quá"`, ...; EN: `"i'm stuck"`, `"no idea"`, `"not
>   sure how"`, ...).  Khi prose match clarification trigger và không
>   có intent đạt `high_conf`, router trả `Clarification` thay vì
>   low-conf guess.  Accuracy quay lại **98.1 %** (102/104) với
>   semantic đúng (entry "không biết làm sao luôn á" pass đúng nhờ
>   route Clarification, không phải vacuous-pass).

Không phải benchmark code-quality (như HumanEval) — đây thuần là
classification accuracy của bộ phân loại keyword + multi-tier weighted
scoring.  Mục đích: đảm bảo prose tiếng Việt + tiếng Anh + slash
typing đều land đúng `/vibe-*` / `/vck-*` slash command.

Cách rerun:

```bash
VIBECODE_UPDATE_PACKAGE="$(pwd)/update-package" \
  PYTHONPATH=./scripts python3 -m pytest \
    tests/test_intent_router_golden.py -v
```

Threshold `0.75` được hard-code trong test.  **KHÔNG hạ ngưỡng** nếu
baseline tụt xuống dưới — sửa router (mở rộng `TIER_1` triggers, điều
chỉnh weight) hoặc cập nhật JSONL kèm methodology note ở đây.

### 4.1 Intent router release matrix dump (PR4)

Mỗi minor / patch release commit kèm 1 file
`benchmarks/intent_router_<VERSION>.json` chứa confusion matrix
deterministic (per-intent tp/fp/fn/tn + per-locale accuracy + miss-pair
clusters).  File này là **release artefact** — diff giữa version cho
biết router cải thiện / regress ở chỗ nào, không cần rerun benchmark.

Schema chi tiết + cách interpret xem `benchmarks/README.md`.

Regenerate sau khi bump VERSION:

```bash
PYTHONPATH=./scripts python3 tools/dump_intent_confusion.py
# → ghi benchmarks/intent_router_<VERSION>.json
```

Test `tests/test_benchmarks_intent_dump.py` ép buộc:

- File `benchmarks/intent_router_<current-VERSION>.json` tồn tại.
- Schema hợp lệ (đủ key bắt buộc, kiểu dữ liệu đúng).
- `set_inclusion_accuracy` ≥ 0.75 (cùng gate golden eval).

## 4b. Observability (PR2 — structured logging)

VibecodeKit xuất structured log cho mọi event security-critical — decision
của ``permission_engine``, scrub của ``hook_interceptor``, tool-call cycle
của ``tool_executor``, denial append của ``denial_store``.  Log được emit
qua helper ``scripts/vibecodekit/_logging.py`` (stdlib-only, không thêm
dependency) và ghi ra ``stderr`` (``stdout`` vẫn là contract của CLI
``print()``).

Env switches:

| Env | Default | Ý nghĩa |
|---|---|---|
| ``VIBECODE_LOG_LEVEL`` | ``INFO`` | ``DEBUG`` / ``INFO`` / ``WARNING`` / ``ERROR`` / ``CRITICAL``; invalid → ``INFO``. |
| ``VIBECODE_LOG_JSON`` | unset | ``=1`` xuất JSON 1-line cho mỗi record (tiện ``jq`` / ELK / Loki pipeline). |

Ví dụ pipe log sang ``jq``:

```bash
VIBECODE_LOG_LEVEL=DEBUG VIBECODE_LOG_JSON=1 \
  PYTHONPATH=./scripts python3 -m vibecodekit.cli demo 2>&1 1>/dev/null \
  | jq 'select(.name == "vibecodekit.permission_engine")'
```

Invariants:

- ``logger.propagate = False`` cho mỗi logger tạo qua helper — tránh bão
  log khi downstream cài root handler (Sentry, DataDog, syslog).
- ``print()`` trong CLI entrypoint (``cli.py``, ``demo.py``, và ``_main``
  của module ``permission_engine`` / ``tool_executor`` / …) **không** bị
  đổi — chúng là contract stdout của ``python -m vibecodekit.<mod>``.
- JSON formatter thuần ``json.dumps`` stdlib — **không** import
  ``structlog`` / ``python-json-logger`` (giữ DNA Python-pure).

Event catalog (stable names, mở rộng theo release):

| Logger | Event | Level | Khi xảy ra |
|---|---|---|---|
| ``vibecodekit.permission_engine`` | ``permission_decision`` | INFO/WARNING | Mỗi deny / denial-fatigue ask / bypass-unsafe override. |
| ``vibecodekit.denial_store`` | ``denial_recorded`` | DEBUG | Mỗi lần append denial vào store (JSONL + fcntl lock). |
| ``vibecodekit.hook_interceptor`` | ``hook_env_scrubbed`` | INFO | Khi env subprocess bị scrub secret. |
| ``vibecodekit.tool_executor`` | ``tool_plan_start`` / ``tool_plan_end`` | INFO | Entry / exit của ``execute_blocks``. |

---

## 5. Roadmap for external benchmarks (Phase 2)

We plan to add external benchmark runs to provide ground-truth quality
numbers.  Candidates (in order of implementation priority):

1. **HumanEval** (164 tasks) — classic function-completion benchmark.
   Low cost (~$5/run), fast (~10 min), well-understood baseline.
2. **MBPP** (974 tasks) — broader function-level benchmark.
3. **SWE-bench Lite** (300 tasks) — real-world bug fixes on real repos.
   Industry-standard for agent evaluation.
4. **BigCodeBench** (1140 tasks) — harder function-level tasks.

Results will be tracked in `benchmarks/` with timestamp + git SHA,
run nightly on `main`, and referenced from this document.

---

## 6. Contributing benchmark results

If you run VCK-HU against any external benchmark, we welcome PRs adding
results to `benchmarks/<benchmark-name>/results.json`.  Include:

- Git SHA of the VCK-HU version tested
- Benchmark version / split used
- Raw pass rate and any relevant metrics
- Hardware / model backend used
- Cost per run

See `CONTRIBUTING.md` for general PR guidelines.
