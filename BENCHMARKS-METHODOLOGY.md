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
