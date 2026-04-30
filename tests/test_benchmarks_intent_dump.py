"""Gate cho ``benchmarks/intent_router_<VERSION>.json`` (PR4).

Mỗi minor / patch release **phải** commit file release-fixed
confusion-matrix dump kèm version hiện tại.  Test này:

1. Đọc ``VERSION`` (single source of truth).
2. Khẳng định file ``benchmarks/intent_router_<VERSION>.json`` tồn tại.
3. Schema hợp lệ (key bắt buộc + kiểu dữ liệu).
4. ``set_inclusion_accuracy`` ≥ 0.75 (cùng gate
   ``test_intent_router_golden.py:_THRESHOLD``).

Khi bump VERSION mà chưa regen → test fail → user phải chạy:

    PYTHONPATH=./scripts python3 tools/dump_intent_confusion.py

trước khi push.  Đây là **invariant guard** chống release artefact
drift.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_BENCHMARKS = _REPO_ROOT / "benchmarks"
_THRESHOLD = 0.75  # đồng bộ với test_intent_router_golden.py


def _read_version() -> str:
    return (_REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()


def _dump_path() -> Path:
    return _BENCHMARKS / f"intent_router_{_read_version()}.json"


def test_release_dump_exists() -> None:
    p = _dump_path()
    assert p.is_file(), (
        f"Release dump bị thiếu: {p.relative_to(_REPO_ROOT)}.\n"
        "Chạy:\n"
        "  PYTHONPATH=./scripts python3 tools/dump_intent_confusion.py\n"
        "rồi commit file mới vào benchmarks/."
    )


def test_release_dump_schema_valid() -> None:
    payload = json.loads(_dump_path().read_text(encoding="utf-8"))

    required = {
        "version": str,
        "router": str,
        "golden_dataset": str,
        "n": int,
        "set_inclusion_accuracy": float,
        "exact_match_accuracy": float,
        "per_locale_set_inclusion": dict,
        "per_intent": dict,
        "miss_pairs": dict,
    }
    for key, kind in required.items():
        assert key in payload, f"Schema thiếu key {key!r}."
        assert isinstance(payload[key], kind), (
            f"Schema sai kiểu key {key!r}: kỳ vọng {kind.__name__}, "
            f"actual {type(payload[key]).__name__}."
        )

    # ``version`` field phải khớp file VERSION.
    assert payload["version"] == _read_version(), (
        f"version trong dump = {payload['version']!r} không khớp "
        f"VERSION = {_read_version()!r}.  Regen dump."
    )

    # per_intent entry phải có đủ tp/fp/fn/tn (int ≥ 0).
    for intent, cm in payload["per_intent"].items():
        for key in ("tp", "fp", "fn", "tn"):
            assert key in cm, (
                f"per_intent[{intent!r}] thiếu {key!r}."
            )
            assert isinstance(cm[key], int) and cm[key] >= 0, (
                f"per_intent[{intent!r}][{key!r}] phải là int ≥ 0, "
                f"actual {cm[key]!r}."
            )


def test_release_dump_meets_accuracy_gate() -> None:
    payload = json.loads(_dump_path().read_text(encoding="utf-8"))
    acc = payload["set_inclusion_accuracy"]
    assert acc >= _THRESHOLD, (
        f"set_inclusion_accuracy = {acc:.4f} < gate {_THRESHOLD:.2f}.  "
        "Sửa intent_router (mở rộng triggers / tinh chỉnh weight) hoặc "
        "cập nhật golden JSONL kèm methodology note ở "
        "BENCHMARKS-METHODOLOGY.md §4."
    )


@pytest.mark.parametrize("locale", ["en", "vi"])
def test_release_dump_per_locale_meets_gate(locale: str) -> None:
    payload = json.loads(_dump_path().read_text(encoding="utf-8"))
    per_locale = payload["per_locale_set_inclusion"]
    assert locale in per_locale, (
        f"per_locale_set_inclusion thiếu locale {locale!r}: {per_locale}"
    )
    acc = per_locale[locale]
    assert acc >= _THRESHOLD, (
        f"per_locale [{locale}] = {acc:.4f} < gate {_THRESHOLD:.2f}."
    )
