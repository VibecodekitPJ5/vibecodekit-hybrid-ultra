#!/usr/bin/env python3
"""Example: run the 7-dimension × 8-axis quality gate on a sample scorecard.

Run from the repo root:
    PYTHONPATH=./scripts python examples/06_quality_gate.py

Demonstrates ``vibecodekit.quality_gate.evaluate``: a fail-if-any-axis-low
release gate (default ``min_axis=0.7``, ``min_aggregate=0.85``).

Two scenarios are exercised:
  1. PASS — all 15 keys ≥ 0.85.
  2. FAIL — one axis dipped to 0.55 (security risk evidence).
"""
from __future__ import annotations

from typing import Optional

from vibecodekit.quality_gate import AXES, DIMENSIONS, evaluate


def make_scorecard(axis_score_overrides: Optional[dict] = None) -> dict:
    """Build a 15-key scorecard (7 dims + 8 axes) with default 0.90."""
    overrides = axis_score_overrides or {}
    sc = {}
    for key in DIMENSIONS + AXES:
        sc[key] = {
            "score": overrides.get(key, 0.90),
            "evidence": "all green" if key not in overrides else "see overrides",
        }
    return sc


def print_verdict(label: str, result: dict) -> None:
    status = "PASS" if result["passed"] else "FAIL"
    agg = result["aggregate"]
    failed = result["failed_below_min"]
    print(f"{label:<28s} {status}  aggregate={agg}  failed_axes={failed}")


if __name__ == "__main__":
    print(f"Gate: 7 dimensions ({len(DIMENSIONS)}) × 8 axes ({len(AXES)})")
    print(f"      min_axis=0.7, min_aggregate=0.85")
    print()

    pass_card = make_scorecard()
    pass_result = evaluate(pass_card)
    print_verdict("Scenario 1 (all green):", pass_result)

    fail_card = make_scorecard({"a_privacy": 0.55})
    fail_result = evaluate(fail_card)
    print_verdict("Scenario 2 (privacy dip):", fail_result)

    assert pass_result["passed"] is True
    assert fail_result["passed"] is False
    assert "a_privacy" in fail_result["failed_below_min"]

    print("\nOK")
