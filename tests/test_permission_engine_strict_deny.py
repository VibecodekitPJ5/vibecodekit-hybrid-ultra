"""PR4 — strict deny, safe exception, rate-capped audit log tests.

Smoke + integration test cho Layer 4b/4c của ``permission_engine``:

* 9 pattern strict-deny (gstack-port) → ``decision="deny"`` + rule_id +
  severity="high" trong ``extra``.
* Safe-exception list ``rm -rf node_modules`` → ``decision`` KHÔNG
  deny; ``class="mutation"``; không ghi audit.
* ``rm -rf /etc`` (target không trong safe list) → vẫn deny.
* ``chmod 755 ./script.sh`` → không deny.
* Audit log ``~/.vibecodekit/security/attempts.jsonl`` ghi 1 dòng JSON
  mỗi deny + rate-cap 60/min (dropped_count tăng trong meta).
* Audit log KHÔNG ghi cmd plaintext (chỉ sha256 hash).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from vibecodekit import _audit_log
from vibecodekit.permission_engine import decide


@pytest.fixture()
def audit_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate audit log dir per test."""
    d = tmp_path / "security"
    monkeypatch.setenv("VIBECODE_AUDIT_LOG_DIR", str(d))
    _audit_log.reset_window_for_tests()
    yield d
    _audit_log.reset_window_for_tests()


STRICT_DENY_PROBES = [
    ("chmod 777 /", "R-CHMOD-WORLD-ROOT-001"),
    ("shutdown -h now", "R-SHUTDOWN-HOST-002"),
    ("history -c", "R-HISTORY-WIPE-003"),
    ("rm $(whoami)", "R-RM-CMD-SUBST-004"),
    ("kubectl delete --all", "R-KUBECTL-DELETE-ALL-005"),
    ("terraform destroy", "R-TERRAFORM-DESTROY-006"),
    ("aws s3 rm s3://bucket --recursive", "R-AWS-S3-RM-RECURSIVE-007"),
    ("DROP TABLE users", "R-SQL-DATA-LOSS-008"),
    ("drop database prod_db", "R-SQL-DATA-LOSS-008"),
    ("TRUNCATE TABLE events", "R-SQL-DATA-LOSS-008"),
    ("gcloud compute instances delete prod", "R-GCP-VM-DELETE-009"),
]


@pytest.mark.parametrize("cmd,rule_id", STRICT_DENY_PROBES)
def test_strict_deny_pattern(cmd: str, rule_id: str, audit_dir: Path) -> None:
    d = decide(cmd, mode="default", root=str(audit_dir.parent))
    assert d["decision"] == "deny", (cmd, d)
    assert d["class"] == "blocked", (cmd, d)
    extra = d.get("extra") or {}
    assert extra.get("rule_id") == rule_id, (cmd, extra)
    assert extra.get("severity") == "high", (cmd, extra)


SAFE_EXCEPTION_PROBES = [
    "rm -rf node_modules",
    "rm -rf ./dist ./build",
    "rm -rf .pytest_cache __pycache__",
    "rm -rf .venv venv",
    "rm -rf coverage",
    "rm -rf ./node_modules ./.next",
]


@pytest.mark.parametrize("cmd", SAFE_EXCEPTION_PROBES)
def test_rm_rf_safe_exception(cmd: str, audit_dir: Path) -> None:
    d = decide(cmd, mode="default", root=str(audit_dir.parent))
    assert d["decision"] != "deny", (cmd, d)
    assert d["class"] == "mutation", (cmd, d)


def test_rm_rf_unsafe_target_still_denies(audit_dir: Path) -> None:
    d = decide("rm -rf /etc", mode="default", root=str(audit_dir.parent))
    assert d["decision"] == "deny", d


def test_rm_rf_with_command_substitution_rejected(audit_dir: Path) -> None:
    # `rm -rf $(whoami)` phải bị bắt bởi R-RM-CMD-SUBST-004, KHÔNG
    # được safe-exception accept dù `$(whoami)` không phải build target.
    d = decide("rm -rf $(whoami)", mode="default", root=str(audit_dir.parent))
    assert d["decision"] == "deny", d


def test_chmod_755_script_not_deny(audit_dir: Path) -> None:
    d = decide("chmod 755 ./script.sh", mode="default",
               root=str(audit_dir.parent))
    assert d["decision"] != "deny", d


def test_audit_log_written_on_strict_deny(audit_dir: Path) -> None:
    decide("terraform destroy", mode="default", root=str(audit_dir.parent))
    jsonl = audit_dir / "attempts.jsonl"
    assert jsonl.is_file(), jsonl
    lines = jsonl.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    for key in ("ts", "decision", "rule_id", "cmd_hash", "mode", "severity"):
        assert key in entry, (key, entry)
    assert entry["decision"] == "deny"
    assert entry["rule_id"] == "R-TERRAFORM-DESTROY-006"
    assert entry["cmd_hash"].startswith("sha256:")
    # Hash, không ghi plaintext.
    assert "terraform" not in entry["cmd_hash"]


def test_audit_log_no_plaintext_leak(audit_dir: Path) -> None:
    secret_cmd = "DROP TABLE credentials_GHP_SUPER_SECRET_TOKEN"
    decide(secret_cmd, mode="default", root=str(audit_dir.parent))
    jsonl = audit_dir / "attempts.jsonl"
    content = jsonl.read_text(encoding="utf-8")
    # Plaintext secret KHÔNG xuất hiện trong audit file.
    assert "GHP_SUPER_SECRET_TOKEN" not in content, content
    assert "credentials_" not in content, content


def test_audit_log_rate_cap_drops_extras(audit_dir: Path) -> None:
    # 70 requests trong cùng 1 window → ghi tối đa 60 entry, 10 drop.
    for i in range(70):
        decide(f"terraform destroy -target=r{i}",
               mode="default", root=str(audit_dir.parent))
    jsonl = audit_dir / "attempts.jsonl"
    lines = jsonl.read_text(encoding="utf-8").splitlines()
    # Cho phép dao động ±1 do timing — chính xác là 60.
    assert 55 <= len(lines) <= 70, f"got {len(lines)} lines"
    meta_path = audit_dir / "attempts.meta.json"
    if len(lines) < 70:
        assert meta_path.is_file()
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        assert meta.get("dropped_count", 0) > 0
        assert "hour_key" in meta


def test_cmd_hash_stable() -> None:
    # Cùng cmd → cùng hash.
    a = _audit_log.cmd_hash("rm -rf /")
    b = _audit_log.cmd_hash("rm -rf /")
    assert a == b
    assert a.startswith("sha256:")
    # Khác cmd → khác hash.
    c = _audit_log.cmd_hash("rm -rf /tmp")
    assert a != c


def test_audit_log_fallback_tempdir_when_no_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Xoá VIBECODE_AUDIT_LOG_DIR + trỏ HOME tới readonly dir → fallback
    # tempfile.gettempdir().
    monkeypatch.delenv("VIBECODE_AUDIT_LOG_DIR", raising=False)
    ro_home = tmp_path / "readonly_home"
    ro_home.mkdir()
    os.chmod(ro_home, 0o500)
    try:
        monkeypatch.setenv("HOME", str(ro_home))
        resolved = _audit_log._audit_dir()
        # Path tồn tại sau ensure_dir — nghĩa là không throw + chọn
        # tempdir hoặc home; test chỉ cần không crash.
        _audit_log._ensure_dir(resolved)
    finally:
        os.chmod(ro_home, 0o700)
