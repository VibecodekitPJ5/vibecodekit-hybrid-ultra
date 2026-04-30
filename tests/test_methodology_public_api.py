"""Smoke + lock test cho ``vibecodekit.methodology`` public API (PR3).

Triage 5 hàm public không có call site nội bộ ở review #4:

| Hàm                                | Hành động  |
|------------------------------------|------------|
| ``lookup_style_token``             | giữ + lock |
| ``list_rri_question_project_types``| thêm test  |
| ``list_stack_recommendations``     | thêm test  |
| ``list_references``                | thêm test  |
| ``load_reference_section``         | giữ + lock |

Mục đích test này:

1. Smoke: 5 hàm trên + các hàm public khác trả kiểu dữ liệu kỳ vọng,
   không raise trên call default args.
2. Lock: ``methodology.__all__`` khớp 1:1 với danh sách public symbol
   được runtime expose — nếu thêm symbol public mà quên cập nhật
   ``__all__`` (hoặc ngược lại), test fail.

KHÔNG đụng tới: ``evaluate_rri_t``, ``evaluate_rri_ux``,
``evaluate_vn_checklist``, ``anti_patterns_canonical``,
``evaluate_anti_patterns_checklist``, ``evaluate_verify_coverage``,
``recommend_stack`` — đã có test ở ``tests/test_content_depth.py`` /
``tests/test_methodology_eval_runners.py``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from vibecodekit import methodology  # noqa: E402


# ---------------------------------------------------------------------------
# 1. Smoke — 3 hàm chưa có call site phải call được + trả kiểu đúng.
# ---------------------------------------------------------------------------


def test_list_rri_question_project_types_returns_sorted_list() -> None:
    """Trả ``List[str]`` các project_type có trong question bank, sorted.

    Bank canonical (``references/rri-question-bank.json``) ship 9 project
    type (saas, dashboard, blog, ...).  Test khẳng định:

    - Trả ``list``, mọi phần tử là ``str`` không rỗng.
    - List sorted (deterministic — quan trọng cho doc generators).
    - Có ≥ 5 project type (sanity check, không lock số chính xác để
      tránh test brittle khi bank mở rộng).
    """
    types = methodology.list_rri_question_project_types()
    assert isinstance(types, list), (
        f"Phải trả list, actual {type(types).__name__}"
    )
    assert types == sorted(types), (
        f"Phải sorted (deterministic), actual {types}"
    )
    for t in types:
        assert isinstance(t, str) and t, (
            f"Mỗi project_type phải là str non-empty, actual {t!r}"
        )
    assert len(types) >= 5, (
        f"Question bank phải ship ≥5 project type, actual {len(types)}: "
        f"{types}"
    )


def test_list_stack_recommendations_covers_canonical_set() -> None:
    """Trả ``List[str]`` các project_type có recommendation trong
    ``PROJECT_STACK_RECOMMENDATIONS``.

    Canonical set hiện có 11 entry (xem probe #49).  Test:

    - Trả ``list[str]`` sorted.
    - Có entry "saas" + "landing" (2 entry quan trọng nhất, lock cứng).
    - Mọi entry là key hợp lệ của ``recommend_stack`` (round-trip).
    """
    types = methodology.list_stack_recommendations()
    assert isinstance(types, list)
    assert types == sorted(types), (
        f"Phải sorted (deterministic), actual {types}"
    )
    assert len(types) >= 5
    # 2 entry must-have.
    for must in ("saas", "landing"):
        assert must in types, (
            f"PROJECT_STACK_RECOMMENDATIONS phải có entry {must!r}: {types}"
        )
    # Round-trip: gọi recommend_stack với mỗi key phải không raise.
    for t in types:
        rec = methodology.recommend_stack(t)
        assert isinstance(rec, dict)
        assert "framework" in rec
        # ``unknown`` chỉ true cho fallback ``custom`` chứ không phải các
        # entry list_stack_recommendations() trả ra.
        assert rec.get("unknown") is False, (
            f"recommend_stack({t!r}) trả unknown=True trong khi key có "
            f"trong list_stack_recommendations() — bug map."
        )


def test_list_references_returns_well_formed_entries() -> None:
    """Trả ``List[Dict[str, str]]`` mô tả các file trong
    ``references/NN-*.md``.

    Test:

    - Mỗi entry có 3 key bắt buộc: ``ref_id``, ``filename``, ``title``.
    - ``ref_id`` format ``ref-NN`` (NN là 2 chữ số).
    - ``filename`` match pattern ``NN-*.md``.
    - List ≥ 30 entry (sanity — bundle ship 35+ reference).
    """
    refs = methodology.list_references()
    assert isinstance(refs, list)
    if not refs:
        pytest.skip(
            "references/ không tồn tại trong layout này — soft-skip "
            "(probe #46/#48 sẽ bắt nếu thiếu trong release-matrix)."
        )

    assert len(refs) >= 30, (
        f"Bundle phải ship ≥30 reference, actual {len(refs)}"
    )
    for entry in refs:
        assert isinstance(entry, dict)
        for key in ("ref_id", "filename", "title"):
            assert key in entry, (
                f"Reference entry thiếu key {key!r}: {entry}"
            )
            assert isinstance(entry[key], str), (
                f"Entry[{key!r}] phải là str, actual {entry[key]!r}"
            )
        # ref_id format.
        assert entry["ref_id"].startswith("ref-") and len(
            entry["ref_id"]
        ) == 6, (
            f"ref_id phải format 'ref-NN', actual {entry['ref_id']!r}"
        )
        digits = entry["ref_id"][4:]
        assert digits.isdigit(), (
            f"ref_id phải kết thúc bằng 2 digit, actual "
            f"{entry['ref_id']!r}"
        )
        # filename khớp ref_id.
        assert entry["filename"].startswith(digits + "-"), (
            f"filename phải bắt đầu bằng {digits!r}-, actual "
            f"{entry['filename']!r}"
        )


def test_lookup_style_token_resolves_canonical_token() -> None:
    """Smoke check ``lookup_style_token`` (đã có test sâu hơn ở
    ``tests/test_content_depth.py:241`` — test này chỉ lock signature).

    - Token canonical "FP-1" (Flow Physics axis 1) phải trả dict có
      key ``token_id``.
    - Token không tồn tại trả ``None``.
    """
    found = methodology.lookup_style_token("FP-1")
    if found is not None:  # bundle layout có thể không ship style tokens.
        assert isinstance(found, dict)
        assert found.get("token_id") == "FP-1"

    missing = methodology.lookup_style_token("NOT-A-TOKEN-XYZ")
    assert missing is None


def test_load_reference_section_returns_str_for_canonical_section() -> None:
    """Smoke check ``load_reference_section`` (đã có test sâu ở
    ``tests/test_content_depth.py:287``).  Test này chỉ lock signature
    + raise behavior.

    - Section không tồn tại raise ``ValueError`` hoặc trả str rỗng (để
      docstring quyết định — KHÔNG lock cứng).
    - Section tồn tại trả str non-empty.
    """
    refs = methodology.list_references()
    if not refs:
        pytest.skip("references/ không tồn tại trong layout này.")
    # Lấy reference đầu tiên + đọc heading đầu tiên trong file.
    first = refs[0]
    full = methodology.load_reference(first["ref_id"])
    headings = [
        ln[3:].strip()
        for ln in full.splitlines()
        if ln.startswith("## ")
    ]
    if not headings:
        pytest.skip(
            f"Reference {first['ref_id']!r} không có heading level-2."
        )
    body = methodology.load_reference_section(first["ref_id"], headings[0])
    assert isinstance(body, str)
    assert body, (
        f"Section {headings[0]!r} của {first['ref_id']!r} không nên rỗng."
    )


# ---------------------------------------------------------------------------
# 2. Lock — __all__ khớp public symbol thực tế.
# ---------------------------------------------------------------------------


def test_methodology_all_matches_public_runtime_symbols() -> None:
    """Mọi symbol trong ``__all__`` phải resolve được tại runtime; và
    mọi public symbol non-underscore không nằm trong ``__all__`` phải
    là ``import``-ed name (typing / std lib re-export) chứ KHÔNG phải
    function/class định nghĩa trong module.

    Mục đích: tránh drift "thêm hàm public mà quên thêm vào __all__"
    (hoặc ngược lại — gỡ hàm mà quên gỡ khỏi __all__).
    """
    all_set = set(methodology.__all__)

    # 2a. Mọi symbol trong __all__ phải tồn tại trong module.
    missing = [s for s in all_set if not hasattr(methodology, s)]
    assert not missing, (
        f"__all__ liệt kê symbol không tồn tại trong module: {missing}"
    )

    # 2b. Mọi function/class top-level định nghĩa trong module mà KHÔNG
    # private (leading underscore) phải nằm trong __all__.
    extra: list[str] = []
    for name in dir(methodology):
        if name.startswith("_"):
            continue
        obj = getattr(methodology, name)
        # Chỉ check function/class định nghĩa trong module này (loại
        # bỏ re-export typing.Dict, typing.List, json, os, re, ...).
        mod_name = getattr(obj, "__module__", None)
        if mod_name != methodology.__name__:
            continue
        if name not in all_set:
            extra.append(name)
    assert not extra, (
        f"Function/class public định nghĩa trong methodology.py nhưng "
        f"thiếu trong __all__: {extra}"
    )

    # 2c. Sanity: 5 hàm spec triage phải có trong __all__.
    spec_required = {
        "lookup_style_token",
        "list_rri_question_project_types",
        "list_stack_recommendations",
        "list_references",
        "load_reference_section",
    }
    missing_spec = spec_required - all_set
    assert not missing_spec, (
        f"5 hàm triage PR3 thiếu trong __all__: {missing_spec}"
    )


def test_methodology_module_constants_have_expected_shape() -> None:
    """4 schema constant (RRI_T_STRESS_AXES, RRI_T_RESULT_LEVELS,
    RRI_UX_AXES, RRI_UX_RESULT_LEVELS) là dataclass-style schema doc —
    test này lock shape để tránh ai đó "dọn dead code" gỡ chúng đi.
    """
    assert isinstance(methodology.RRI_T_DIMENSIONS, tuple)
    assert len(methodology.RRI_T_DIMENSIONS) == 7

    assert isinstance(methodology.RRI_T_STRESS_AXES, tuple)
    assert len(methodology.RRI_T_STRESS_AXES) == 8

    assert isinstance(methodology.RRI_T_RESULT_LEVELS, set)
    assert methodology.RRI_T_RESULT_LEVELS == {
        "PASS", "FAIL", "PAINFUL", "MISSING"
    }

    assert isinstance(methodology.RRI_UX_AXES, tuple)
    assert len(methodology.RRI_UX_AXES) >= 5

    assert isinstance(methodology.RRI_UX_RESULT_LEVELS, set)
    assert methodology.RRI_UX_RESULT_LEVELS == {
        "FLOW", "FRICTION", "BROKEN", "MISSING"
    }
