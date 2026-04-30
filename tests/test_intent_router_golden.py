"""Golden eval cho :class:`IntentRouter`.

Mục tiêu: thay thế cách demo cherry-pick 3 ví dụ bằng dataset có nhãn
≥ 100 dòng (40 EN clear + 40 VI clear + 20 edge / ambiguous).  Test
tính:

- ``set_inclusion_accuracy = mean(expected ⊆ actual)`` — gate **≥ 0.75**.
- ``exact_match_accuracy = mean(expected == actual)`` — báo cáo only,
  **không** gate (vì router được phép trả thêm intent là superset).
- Confusion matrix per intent — báo cáo only, dump khi accuracy fail.

**KHÔNG** hạ threshold 0.75 nếu baseline tụt xuống dưới — sửa router
hoặc cập nhật JSONL (kèm methodology note).  Threshold sửa cứng trong
test này, **KHÔNG** đọc từ env var để tránh CI bypass im lặng.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import pytest

# scripts/ phải có trong sys.path (CI inject qua PYTHONPATH; local sẽ
# fallback ở đây).
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from vibecodekit.intent_router import (  # noqa: E402
    Clarification,
    IntentRouter,
)

_GOLDEN = _REPO_ROOT / "tests" / "fixtures" / "intent_router_golden.jsonl"
_THRESHOLD = 0.75  # hard-coded; xem docstring.


def _load_golden() -> list[dict]:
    out: list[dict] = []
    for ln_no, raw in enumerate(_GOLDEN.read_text().splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            raise AssertionError(
                f"{_GOLDEN.name}:{ln_no} không phải JSON hợp lệ: {exc}"
            ) from exc
        entry["_line"] = ln_no
        out.append(entry)
    return out


def test_golden_dataset_is_well_formed() -> None:
    entries = _load_golden()
    assert len(entries) >= 100, (
        f"Golden dataset cần ≥100 dòng, hiện có {len(entries)}.  "
        "Bổ sung trong tests/fixtures/intent_router_golden.jsonl."
    )
    # Phân bổ tối thiểu: 30 EN + 30 VI + 10 edge/ambiguous.
    by_locale = defaultdict(int)
    by_tag = defaultdict(int)
    for e in entries:
        by_locale[e["locale"]] += 1
        by_tag[e["tag"]] += 1
    assert by_locale.get("en", 0) >= 30, (
        f"Locale EN cần ≥30 entry, hiện {by_locale.get('en', 0)}."
    )
    assert by_locale.get("vi", 0) >= 30, (
        f"Locale VI cần ≥30 entry, hiện {by_locale.get('vi', 0)}."
    )
    assert (
        by_tag.get("ambiguous", 0) + by_tag.get("edge", 0)
    ) >= 10, (
        "Cần ≥10 entry có tag ambiguous / edge để stress test khả năng "
        "clarify + multi-intent."
    )


def _classify(router: IntentRouter, prose: str) -> set[str]:
    m = router.classify(prose)
    if isinstance(m, Clarification):
        return set()
    return set(m.intents)


def _compute_confusion_matrix(
    entries: list[dict], router: IntentRouter | None = None
) -> dict[str, object]:
    """Tính metrics deterministic cho golden set.

    Trả ``dict`` với key sorted để JSON dump ra cùng 1 byte stream
    cho cùng (router, golden):

    - ``set_inclusion_accuracy``: float
    - ``exact_match_accuracy``: float
    - ``per_locale_set_inclusion``: dict[locale, accuracy]
    - ``per_intent`` (multi-label confusion):
        {intent: {tp, fp, fn, tn}} với:
          tp = entry mà intent ∈ expected ∩ actual
          fp = entry mà intent ∈ actual \\ expected
          fn = entry mà intent ∈ expected \\ actual
          tn = entry mà intent ∉ expected ∪ actual
    - ``miss_pairs``: dict["expected_sorted -> actual_sorted", count]
        Top-N off-diagonal cluster để spot lỗi router phổ biến.

    Helper được tách từ logic test để tái dùng trong
    ``tools/dump_intent_confusion.py`` (PR4 release dump).
    """
    router = router or IntentRouter()
    n = len(entries)
    if n == 0:
        return {
            "set_inclusion_accuracy": 0.0,
            "exact_match_accuracy": 0.0,
            "per_locale_set_inclusion": {},
            "per_intent": {},
            "miss_pairs": {},
            "n": 0,
        }

    # Discover intent universe = union(expected) ∪ union(actual_seen).
    actuals: list[set[str]] = []
    expecteds: list[set[str]] = []
    locales: list[str] = []
    for entry in entries:
        expected = set(entry["expected_intents"])
        actual = _classify(router, entry["prose"])
        expecteds.append(expected)
        actuals.append(actual)
        locales.append(entry.get("locale", "unknown"))

    universe: set[str] = set()
    for s in expecteds + actuals:
        universe.update(s)

    # Set-inclusion + exact-match accuracy.
    si_pass = sum(1 for e, a in zip(expecteds, actuals) if _entry_passes(e, a))
    em_pass = sum(1 for e, a in zip(expecteds, actuals) if e == a)

    # Per-locale set-inclusion.
    by_locale: dict[str, list[bool]] = defaultdict(list)
    for loc, e, a in zip(locales, expecteds, actuals):
        by_locale[loc].append(_entry_passes(e, a))
    per_locale = {
        loc: round(sum(passes) / len(passes), 6) if passes else 0.0
        for loc, passes in sorted(by_locale.items())
    }

    # Per-intent confusion (binary classification per intent).
    per_intent: dict[str, dict[str, int]] = {}
    for intent in sorted(universe):
        tp = fp = fn = tn = 0
        for e, a in zip(expecteds, actuals):
            in_e = intent in e
            in_a = intent in a
            if in_e and in_a:
                tp += 1
            elif in_a and not in_e:
                fp += 1
            elif in_e and not in_a:
                fn += 1
            else:
                tn += 1
        per_intent[intent] = {"tp": tp, "fp": fp, "fn": fn, "tn": tn}

    # Top miss-pair cluster (off-diagonal, sorted descending).
    miss_pairs_counter: dict[str, int] = defaultdict(int)
    for e, a in zip(expecteds, actuals):
        if e == a:
            continue
        key = (
            f"expected={sorted(e) if e else ['<Clarification>']}"
            f" -> actual={sorted(a) if a else ['<Clarification>']}"
        )
        miss_pairs_counter[key] += 1
    miss_pairs = dict(
        sorted(miss_pairs_counter.items(), key=lambda kv: (-kv[1], kv[0]))
    )

    return {
        "n": n,
        "set_inclusion_accuracy": round(si_pass / n, 6),
        "exact_match_accuracy": round(em_pass / n, 6),
        "per_locale_set_inclusion": per_locale,
        "per_intent": per_intent,
        "miss_pairs": miss_pairs,
    }


def _entry_passes(expected: set[str], actual: set[str]) -> bool:
    """Set-inclusion check, **closed under empty expected**.

    Khi ``expected_intents == []`` (entry tag ``ambiguous``, kỳ vọng
    router trả ``Clarification``), ``expected.issubset(actual)`` luôn
    True (empty set là subset của mọi set) → vacuously pass.  Đây là
    bug Devin Review báo trên PR3 (#28): 10 entry ambiguous trở thành
    no-op, inflate accuracy mà không test gì.

    Fix: khi ``expected`` rỗng, yêu cầu ``actual`` cũng phải rỗng
    (router trả ``Clarification`` → set rỗng theo ``_classify``).
    """
    if not expected:
        return len(actual) == 0
    return expected.issubset(actual)


def test_intent_router_set_inclusion_accuracy() -> None:
    router = IntentRouter()
    entries = _load_golden()
    matches = 0
    misses: list[tuple[int, str, list[str], list[str]]] = []
    for entry in entries:
        expected = set(entry["expected_intents"])
        actual = _classify(router, entry["prose"])
        if _entry_passes(expected, actual):
            matches += 1
        else:
            misses.append(
                (
                    entry["_line"],
                    entry["prose"][:80],
                    sorted(expected),
                    sorted(actual),
                )
            )
    accuracy = matches / len(entries)
    msg_lines = [
        f"Set-inclusion accuracy = {matches}/{len(entries)} "
        f"= {accuracy:.3f} (gate ≥ {_THRESHOLD:.2f}).",
    ]
    if misses:
        msg_lines.append(f"Misses ({len(misses)}):")
        for ln, prose, exp, act in misses[:25]:
            msg_lines.append(
                f"  L{ln} prose={prose!r}\n"
                f"        expected={exp}\n"
                f"        actual  ={act}"
            )
        if len(misses) > 25:
            msg_lines.append(f"  ... và {len(misses) - 25} dòng nữa")
    assert accuracy >= _THRESHOLD, "\n".join(msg_lines)


def test_intent_router_exact_match_accuracy_is_reported() -> None:
    """Exact-match accuracy KHÔNG gate (router có thể trả superset
    hợp lệ); test này chỉ đảm bảo metric tính được + log lại để dễ
    monitor drift."""
    router = IntentRouter()
    entries = _load_golden()
    exact = 0
    for entry in entries:
        expected = set(entry["expected_intents"])
        actual = _classify(router, entry["prose"])
        if expected == actual:
            exact += 1
    rate = exact / len(entries)
    # Hard-fail nếu exact rate giảm thê thảm (< 0.50) — báo hiệu router
    # đột nhiên trả super set quá rộng.  Threshold mềm hơn set-inclusion.
    assert rate >= 0.50, (
        f"Exact-match accuracy = {exact}/{len(entries)} = {rate:.3f}; "
        "ngưỡng cảnh báo 0.50.  Router có thể đang trả superset quá rộng."
    )


def test_clarification_trigger_overrides_low_conf_keyword() -> None:
    """Regression test cho follow-up sau PR3 — bug "không biết làm sao
    luôn á" → ``{BUILD}`` (chỉ vì ``"làm"`` nằm trong BUILD trigger).

    Sau fix: prose chứa ``_CLARIFICATION_TRIGGERS`` (vd. ``"không biết"``,
    ``"luôn á"``, ``"làm sao"``) PHẢI route ``Clarification`` khi
    không có intent nào đạt ``high_conf``.  Test parametrize 4 case:

    1. Pure uncertainty + 1 yếu BUILD keyword → Clarification.
    2. Uncertainty + clear deploy keyword → Clarification (deploy
       đơn lẻ score 0.51 < high_conf 0.55, không đủ override).  Đây
       là behavior CONSERVATIVE đúng: user đang bí thì hỏi lại,
       không guess.
    3. Pipeline trigger ("làm shop online") vẫn fire FULL_BUILD bất
       kể có clarification trigger trong prose hay không (pipeline
       check chạy trước).
    4. Câu rõ ràng (không có uncertainty marker) vẫn route bình
       thường.
    """
    router = IntentRouter()

    # Case 1 — bug nguyên thủy.
    m = router.classify("không biết làm sao luôn á")
    assert isinstance(m, Clarification), (
        f"Bug regress: 'không biết làm sao luôn á' phải trả Clarification, "
        f"router trả intents={getattr(m, 'intents', None)}"
    )

    # Case 2 — bí + deploy yếu.
    m = router.classify("không biết deploy lên Vercel kiểu nào")
    assert isinstance(m, Clarification), (
        "Prose chứa marker bí + 'deploy' đơn lẻ (score < high_conf) "
        "phải trả Clarification — router không được guess SHIP khi user "
        "đang bí về 'kiểu nào'."
    )

    # Case 3 — pipeline trigger thắng, clarification trigger không che.
    m = router.classify("không biết gì luôn nhưng muốn làm shop online")
    assert not isinstance(m, Clarification), (
        "Pipeline trigger 'shop online' phải fire FULL_BUILD bất kể "
        "uncertainty marker."
    )
    assert "BUILD" in m.intents

    # Case 4 — câu rõ ràng, không có uncertainty marker.
    m = router.classify("review my code for security")
    assert not isinstance(m, Clarification)
    assert "VCK_REVIEW" in m.intents


@pytest.mark.parametrize(
    "locale,min_acc",
    [
        ("en", 0.75),
        ("vi", 0.75),
    ],
)
def test_intent_router_per_locale_accuracy(locale: str, min_acc: float) -> None:
    """Đảm bảo accuracy không "lệch" sang một locale duy nhất.  Nếu
    accuracy EN cao mà VI thấp → router có vấn đề với normalisation
    diacritic, không phải pass do data bias."""
    router = IntentRouter()
    entries = [e for e in _load_golden() if e["locale"] == locale]
    matches = sum(
        1
        for e in entries
        if _entry_passes(
            set(e["expected_intents"]),
            _classify(router, e["prose"]),
        )
    )
    accuracy = matches / len(entries)
    assert accuracy >= min_acc, (
        f"Per-locale set-inclusion accuracy ({locale}) = {matches}/"
        f"{len(entries)} = {accuracy:.3f} < {min_acc:.2f}."
    )
