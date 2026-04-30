#!/usr/bin/env python3
"""Dump confusion matrix + accuracy metrics deterministic cho IntentRouter.

Đầu ra: ``benchmarks/intent_router_<VERSION>.json``.

Mục đích (PR4 sau review #4):

- Trước đây confusion matrix chỉ dump khi golden eval **fail** (debug
  artefact ad-hoc).  Release note giữa các minor version cần baseline
  cố định để so sánh router accuracy theo thời gian.
- Script này stdlib-only, không phụ thuộc pytest.  Có thể chạy thủ
  công sau mỗi bump VERSION (xem ``BENCHMARKS-METHODOLOGY.md``).

Schema:

    {
      "version": "<VERSION>",
      "router": "vibecodekit.intent_router.IntentRouter",
      "golden_dataset": "tests/fixtures/intent_router_golden.jsonl",
      "n": <int>,
      "set_inclusion_accuracy": <float>,
      "exact_match_accuracy": <float>,
      "per_locale_set_inclusion": { "<locale>": <float>, ... },
      "per_intent": { "<INTENT>": {"tp", "fp", "fn", "tn"}, ... },
      "miss_pairs": { "<expected> -> <actual>": <count>, ... }
    }

Sorted keys → file output deterministic cho cùng (router, golden).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO_ROOT / "scripts"
_TESTS = _REPO_ROOT / "tests"
_BENCHMARKS = _REPO_ROOT / "benchmarks"


def _read_version() -> str:
    """Single-source-of-truth từ file ``VERSION``."""
    vfile = _REPO_ROOT / "VERSION"
    if not vfile.is_file():
        raise SystemExit(f"VERSION file không tồn tại: {vfile}")
    return vfile.read_text(encoding="utf-8").strip()


def main() -> int:
    if str(_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS))
    if str(_TESTS) not in sys.path:
        sys.path.insert(0, str(_TESTS))

    # Import sau khi đã set sys.path.
    from test_intent_router_golden import (  # noqa: E402
        _compute_confusion_matrix,
        _load_golden,
    )

    version = _read_version()
    entries = _load_golden()
    metrics = _compute_confusion_matrix(entries)

    payload = {
        "version": version,
        "router": "vibecodekit.intent_router.IntentRouter",
        "golden_dataset": "tests/fixtures/intent_router_golden.jsonl",
        **metrics,
    }

    _BENCHMARKS.mkdir(parents=True, exist_ok=True)
    out = _BENCHMARKS / f"intent_router_{version}.json"
    out.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )

    print(f"wrote {out.relative_to(_REPO_ROOT)}")
    print(f"  n={metrics['n']}")
    print(f"  set_inclusion_accuracy={metrics['set_inclusion_accuracy']}")
    print(f"  exact_match_accuracy={metrics['exact_match_accuracy']}")
    print(f"  per_locale={metrics['per_locale_set_inclusion']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
