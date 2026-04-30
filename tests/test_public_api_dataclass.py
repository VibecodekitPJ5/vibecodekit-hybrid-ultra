"""PR5 — typed public API (``PermissionDecision`` + ``decide_typed``).

Verify dual-shape additive contract:

* ``decide()`` dict return (legacy) vẫn hoạt động.
* ``decide_typed()`` trả về frozen ``PermissionDecision`` dataclass.
* Round-trip parity: cùng cmd → cùng ``decision`` / ``reason`` field
  giữa hai API.
* ``matched_rule_id`` + ``severity`` được surface đúng cho
  Layer 4b strict-deny.
* ``DeprecationWarning`` emit khi gọi ``decide()`` (dưới filter default
  bị ẩn; cần explicit ``simplefilter("default")``).
* ``frozen=True`` → dataclass hashable.

``scaffold_engine.ScaffoldPlan`` / ``ScaffoldResult`` đã được typed từ
trước — PR5 không thêm wrapper; chỉ verify shape existing.
"""
from __future__ import annotations

import warnings
from pathlib import Path

import pytest

from vibecodekit import permission_engine as pe
from vibecodekit.permission_engine import (
    PermissionDecision,
    decide,
    decide_typed,
)
from vibecodekit.scaffold_engine import ScaffoldPlan, ScaffoldResult


@pytest.fixture(autouse=True)
def _isolate_audit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("VIBECODE_AUDIT_LOG_DIR", str(tmp_path / "audit"))
    # Reset deprecation warning flag cho mỗi test để
    # ``test_decide_emits_deprecation_warning`` có thể quan sát.
    monkeypatch.setattr(pe, "_DECIDE_DEPRECATION_WARNED", False)


ROUND_TRIP_PROBES = [
    ("rm -rf /", "deny"),
    ("terraform destroy", "deny"),
    ("chmod 777 /", "deny"),
    ("DROP TABLE users", "deny"),
    ("rm -rf node_modules", "ask"),
    ("echo hi", "ask"),
]


@pytest.mark.parametrize("cmd,expected_decision", ROUND_TRIP_PROBES)
def test_decide_vs_decide_typed_round_trip(
    cmd: str, expected_decision: str, tmp_path: Path
) -> None:
    """Legacy dict và typed dataclass phải nhất quán."""
    root = str(tmp_path)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        raw = decide(cmd, mode="default", root=root)
    typed = decide_typed(cmd, mode="default", root=root)
    assert raw["decision"] == typed.decision
    assert raw["reason"] == typed.reason


def test_decide_typed_returns_frozen_dataclass() -> None:
    d = decide_typed("ls")
    assert isinstance(d, PermissionDecision)
    # Frozen → không set attribute sau khởi tạo.
    with pytest.raises((AttributeError, Exception)):
        d.decision = "deny"  # type: ignore[misc]


def test_decide_typed_hashable_and_usable_in_set() -> None:
    a = decide_typed("ls")
    b = decide_typed("ls")
    c = decide_typed("rm -rf /")
    assert hash(a) == hash(b)
    s = {a, b, c}
    # a == b (cùng cmd, deterministic) → set có 2 member.
    assert len(s) == 2


def test_decide_typed_strict_deny_exposes_rule_id(tmp_path: Path) -> None:
    d = decide_typed("terraform destroy", mode="default", root=str(tmp_path))
    assert d.decision == "deny"
    assert d.matched_rule_id == "R-TERRAFORM-DESTROY-006"
    assert d.severity == "high"


def test_decide_typed_dangerous_pattern_fallback_severity(
    tmp_path: Path,
) -> None:
    # `rm -rf /` khớp Layer 4 generic (không Layer 4b strict) →
    # severity="medium", matched_rule_id=None.
    d = decide_typed("rm -rf /", mode="default", root=str(tmp_path))
    assert d.decision == "deny"
    assert d.matched_rule_id is None
    assert d.severity == "medium"


def test_decide_typed_allow_decision_low_severity(tmp_path: Path) -> None:
    d = decide_typed("ls", mode="default", root=str(tmp_path))
    assert d.decision == "allow"
    assert d.matched_rule_id is None
    assert d.severity == "low"


def test_decide_emits_deprecation_warning_once(tmp_path: Path) -> None:
    """DeprecationWarning emit trên lần đầu gọi ``decide()``."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        decide("ls", mode="default", root=str(tmp_path))
        decide("pwd", mode="default", root=str(tmp_path))
        decide("whoami", mode="default", root=str(tmp_path))
    deprecation_warnings = [
        w for w in caught if issubclass(w.category, DeprecationWarning)
    ]
    assert len(deprecation_warnings) == 1, deprecation_warnings
    msg = str(deprecation_warnings[0].message)
    assert "decide_typed" in msg
    assert "v1.0.0" in msg


def test_as_legacy_dict_contains_core_fields(tmp_path: Path) -> None:
    d = decide_typed("terraform destroy", mode="default", root=str(tmp_path))
    leg = d.as_legacy_dict()
    assert leg["decision"] == "deny"
    assert leg["reason"]
    assert leg["extra"] == {
        "severity": "high",
        "rule_id": "R-TERRAFORM-DESTROY-006",
    }


def test_as_legacy_dict_allow_has_no_rule_id(tmp_path: Path) -> None:
    d = decide_typed("ls", mode="default", root=str(tmp_path))
    leg = d.as_legacy_dict()
    assert leg["extra"] == {"severity": "low"}
    assert "rule_id" not in leg["extra"]  # type: ignore[operator]


# -- ScaffoldEngine pre-existing typed API smoke ----------------------------


def test_scaffold_plan_is_frozen_dataclass() -> None:
    """``ScaffoldPlan`` đã được typed dataclass từ trước PR5 — smoke check."""
    import dataclasses

    assert dataclasses.is_dataclass(ScaffoldPlan)
    params = getattr(ScaffoldPlan, "__dataclass_params__", None)
    assert params is not None
    assert params.frozen is True


def test_scaffold_result_is_frozen_dataclass() -> None:
    import dataclasses

    assert dataclasses.is_dataclass(ScaffoldResult)
    params = getattr(ScaffoldResult, "__dataclass_params__", None)
    assert params is not None
    assert params.frozen is True


def test_permission_engine_all_exports_typed_api() -> None:
    """``__all__`` phải expose ``PermissionDecision`` + ``decide_typed``."""
    assert "PermissionDecision" in pe.__all__
    assert "decide_typed" in pe.__all__
    assert "decide" in pe.__all__  # dual-shape — legacy vẫn exported.
