"""Unit tests for diff-based test selection."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from vibecodekit import eval_select


def test_select_by_exact_match():
    res = eval_select.select_tests(
        ["src/a.py"],
        {"tests/a.py": ["src/a.py"]},
    )
    assert list(res.selected) == ["tests/a.py"]
    assert not res.unmapped_changes


def test_select_by_glob():
    res = eval_select.select_tests(
        ["src/deep/x.py"],
        {"tests/deep.py": ["src/deep/*.py"]},
    )
    assert list(res.selected) == ["tests/deep.py"]


def test_always_run_is_selected_when_not_matched():
    res = eval_select.select_tests(
        ["src/a.py"],
        {"tests/a.py": ["src/a.py"],
         "tests/smoke.py": {"files": [], "always_run": True}},
    )
    assert set(res.selected) == {"tests/a.py", "tests/smoke.py"}
    assert set(res.always_run) == {"tests/smoke.py"}


def test_unmapped_changes_reported():
    res = eval_select.select_tests(
        ["src/a.py", "docs/x.md"],
        {"tests/a.py": ["src/a.py"]},
    )
    assert "docs/x.md" in res.unmapped_changes
    assert "src/a.py" not in res.unmapped_changes


def test_empty_diff_runs_only_always():
    res = eval_select.select_tests(
        [],
        {"tests/a.py": ["src/a.py"],
         "tests/smoke.py": {"files": [], "always_run": True}},
    )
    assert list(res.selected) == ["tests/smoke.py"]


def test_empty_diff_with_fallback_runs_all():
    res = eval_select.select_tests(
        [],
        {"tests/a.py": ["src/a.py"]},
        fallback_all_tests=["tests/a.py", "tests/b.py"],
    )
    assert set(res.selected) == {"tests/a.py", "tests/b.py"}


def test_load_map_accepts_both_shapes(tmp_path: Path):
    p = tmp_path / "map.json"
    p.write_text(json.dumps({
        "tests/list.py": ["src/list/*.py"],
        "tests/dict.py": {"files": ["src/dict/*.py"], "always_run": True},
    }))
    tmap = eval_select.load_map(p)
    assert "tests/list.py" in tmap and "tests/dict.py" in tmap
    assert "__ALWAYS__" in tmap["tests/dict.py"]


def test_load_map_rejects_bad_shape(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"tests/x.py": "oops"}))
    with pytest.raises(ValueError):
        eval_select.load_map(p)


def test_extra_always_run_wins_even_without_map_entry():
    res = eval_select.select_tests(
        ["src/a.py"],
        {"tests/a.py": ["src/a.py"]},
        extra_always_run=["tests/smoke.py"],
    )
    assert "tests/smoke.py" in res.selected


def test_git_changed_files_tolerates_missing_repo(tmp_path: Path):
    # Running outside a repo: either returns [] or doesn't crash.
    got = eval_select.git_changed_files(base="origin/main", cwd=tmp_path)
    assert isinstance(got, list)
