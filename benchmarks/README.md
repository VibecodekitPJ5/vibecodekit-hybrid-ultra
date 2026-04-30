# `benchmarks/` — Release-fixed metric dumps

Mỗi minor release của VibecodeKit Hybrid Ultra commit kèm 1 file
`<artefact>_<version>.json` chứa số đo deterministic. Mục đích:

- **So sánh giữa version**: regression dễ đọc bằng git diff (`git diff
  benchmarks/intent_router_0.16.1.json benchmarks/intent_router_0.16.2.json`)
  cho thấy ngay set-inclusion / exact-match thay đổi.
- **Audit trail**: release note có thể link đúng commit + file dump
  thay vì rerun benchmark (tốn thời gian + non-deterministic nếu môi
  trường khác).
- **CI gate**: `tests/test_benchmarks_intent_dump.py` ép buộc file
  `intent_router_<current-version>.json` tồn tại + schema hợp lệ +
  set-inclusion ≥ 0.75 (cùng threshold golden eval).

## File hiện có

| File | Generator | Schema |
|---|---|---|
| `intent_router_<VERSION>.json` | `tools/dump_intent_confusion.py` | xem dưới |

## Schema `intent_router_*.json`

```json
{
  "version": "0.16.2",
  "router": "vibecodekit.intent_router.IntentRouter",
  "golden_dataset": "tests/fixtures/intent_router_golden.jsonl",
  "n": 104,
  "set_inclusion_accuracy": 0.980769,
  "exact_match_accuracy": 0.894231,
  "per_locale_set_inclusion": { "en": 0.96, "vi": 1.0 },
  "per_intent": {
    "BUILD":  { "tp": 12, "fp":  3, "fn": 1, "tn": 88 },
    "VCK_REVIEW": { "tp": 4, "fp": 0, "fn": 0, "tn": 100 }
  },
  "miss_pairs": {
    "expected=['BUILD'] -> actual=['BUILD', 'SHIP']": 2
  }
}
```

- `set_inclusion_accuracy = mean(expected ⊆ actual)` — gate ≥ 0.75
  (xem `tests/test_intent_router_golden.py:_THRESHOLD`).
- `exact_match_accuracy = mean(expected == actual)` — báo cáo only,
  không gate (router được phép trả superset hợp lệ).
- `per_locale_set_inclusion`: gate ≥ 0.75 mỗi locale (en / vi).
- `per_intent`: confusion binary per-intent (tp/fp/fn/tn).
- `miss_pairs`: top off-diagonal cluster, sorted descending.

## Khi nào regenerate?

Chạy script khi:

1. Bump `VERSION` (mọi minor / patch). `tools/sync_version.py` không
   tự gọi script này — phải chạy thủ công sau bump:

   ```bash
   PYTHONPATH=./scripts python3 tools/dump_intent_confusion.py
   ```

2. Sửa `intent_router.py` → tạo dump mới ở **cùng version cũ** trước
   để diff baseline; sau đó bump version + dump lại.

3. Sửa `tests/fixtures/intent_router_golden.jsonl` → dump lại + giải
   thích trong PR body.

## Interpret kết quả

| Metric | Tăng | Giảm |
|---|---|---|
| `set_inclusion_accuracy` | 🟢 router cover thêm intent đúng | 🔴 regression — mở ngay PR fix |
| `exact_match_accuracy` | 🟢 router không trả superset thừa | 🟡 chấp nhận được nếu set-inclusion vẫn cao (router rộng tay hơn) |
| `per_intent.fp` | 🔴 false positive — router gắn intent sai | — |
| `per_intent.fn` | 🔴 false negative — router miss intent đúng | — |
| `miss_pairs` đột biến cluster mới | 🔴 spot bug pattern | — |

## Không làm ở đây

- KHÔNG chạy benchmark cần API key / external network (HumanEval,
  SWE-bench, ...) — `benchmarks/` chỉ chứa output deterministic stdlib.
- KHÔNG hard-code threshold `0.75` ở chỗ khác. Threshold cứng trong
  `tests/test_intent_router_golden.py:_THRESHOLD`; muốn đổi → sửa 1
  chỗ + ghi chú trong PR body.
