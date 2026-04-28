"""Unit tests for learnings store + team_mode."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from vibecodekit import learnings, team_mode


# ---------------------------------------------------------------------------
# Learnings
# ---------------------------------------------------------------------------

def test_capture_and_load_project(tmp_path: Path):
    rec = learnings.capture("Cache key needs tenant id", root=tmp_path,
                            tags=["cache"], author="alice")
    assert rec.captured_ts > 0
    assert rec.scope == "project"
    loaded = learnings.project_store(tmp_path).load()
    assert len(loaded) == 1
    assert loaded[0].text == "Cache key needs tenant id"
    assert "cache" in loaded[0].tags
    assert loaded[0].author == "alice"


def test_team_and_user_scopes(tmp_path: Path):
    home = tmp_path / "home"
    learnings.capture("team lesson", scope="team", root=tmp_path)
    learnings.capture("user lesson", scope="user", home=home)
    assert len(learnings.team_store(tmp_path).load()) == 1
    assert len(learnings.user_store(home).load()) == 1
    merged = learnings.load_all(root=tmp_path, home=home)
    texts = {l.text for l in merged}
    assert {"team lesson", "user lesson"} <= texts


def test_load_ignores_corrupt_lines(tmp_path: Path):
    store = learnings.project_store(tmp_path)
    store.append(learnings.Learning(text="good", scope="project"))
    # Append a corrupt JSON line.
    with open(store.path, "a", encoding="utf-8") as f:
        f.write("NOT JSON\n")
        f.write(json.dumps({"text": "also good", "scope": "project"}) + "\n")
    recs = store.load()
    assert {r.text for r in recs} == {"good", "also good"}


def test_append_is_atomic_concurrent(tmp_path: Path):
    """Two threads appending 50 records each should yield 100 parseable records."""
    import threading
    store = learnings.project_store(tmp_path)

    def worker(prefix: str):
        for i in range(50):
            store.append(learnings.Learning(text=f"{prefix}-{i}", scope="project"))

    a = threading.Thread(target=worker, args=("a",))
    b = threading.Thread(target=worker, args=("b",))
    a.start(); b.start(); a.join(); b.join()

    recs = store.load()
    assert len(recs) == 100
    assert len({r.text for r in recs}) == 100


def test_learning_from_dict_tolerates_defaults():
    rec = learnings.Learning.from_dict({"text": "x"})
    assert rec.text == "x"
    assert rec.scope == "project"
    assert rec.tags == ()


# ---------------------------------------------------------------------------
# team_mode
# ---------------------------------------------------------------------------

def test_is_team_mode_false_on_empty(tmp_path: Path):
    assert not team_mode.is_team_mode(root=tmp_path)
    assert team_mode.read_team_config(root=tmp_path) is None


def test_write_and_read_round_trip(tmp_path: Path):
    cfg = team_mode.TeamConfig(team_id="platform",
                               required=("/vck-review", "/vck-qa-only"),
                               optional=("/vck-cso",),
                               learnings_required=True)
    written = team_mode.write_team_config(cfg, root=tmp_path)
    assert written.created_ts > 0
    assert written.updated_ts >= written.created_ts
    read = team_mode.read_team_config(root=tmp_path)
    assert read is not None
    assert read.team_id == "platform"
    assert set(read.required) == {"/vck-review", "/vck-qa-only"}
    assert read.learnings_required is True


def test_assert_required_gates_run_raises(tmp_path: Path):
    team_mode.write_team_config(
        team_mode.TeamConfig(team_id="t", required=("/vck-review",)),
        root=tmp_path,
    )
    with pytest.raises(team_mode.TeamGateViolation):
        team_mode.assert_required_gates_run([], root=tmp_path)
    # Passing the required gate does not raise.
    team_mode.assert_required_gates_run(["/vck-review"], root=tmp_path)


def test_no_team_file_is_noop(tmp_path: Path):
    # Without team.json, assert_required_gates_run must be a silent no-op.
    team_mode.assert_required_gates_run([], root=tmp_path)


def test_corrupt_team_file_returns_none(tmp_path: Path):
    (tmp_path / ".vibecode").mkdir()
    (tmp_path / team_mode.TEAM_FILE).write_text("NOT JSON", encoding="utf-8")
    assert team_mode.read_team_config(root=tmp_path) is None


def test_write_preserves_created_ts_on_update(tmp_path: Path):
    cfg = team_mode.TeamConfig(team_id="t", required=())
    first = team_mode.write_team_config(cfg, root=tmp_path)
    # Simulate a second update.
    second = team_mode.write_team_config(
        team_mode.TeamConfig(team_id="t", required=("/vck-qa",)),
        root=tmp_path,
    )
    assert second.created_ts == first.created_ts
    assert second.updated_ts >= first.updated_ts
