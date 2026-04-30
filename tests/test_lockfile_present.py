"""CI guard cho PR3 — uv.lock hiện diện + parse được.

Scope tối thiểu (không over-specify để tránh drift khi bump version):

* `uv.lock` tồn tại ở repo root.
* File có header `version = ` (format uv > 0.5).
* Có tối thiểu vài package snapshot (> 10) — đảm bảo không rỗng.
* Các workflow CI supply-chain cần thiết được commit.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_uv_lock_present() -> None:
    path = REPO_ROOT / "uv.lock"
    assert path.is_file(), f"Expected uv.lock at {path}"


def test_uv_lock_has_header() -> None:
    text = (REPO_ROOT / "uv.lock").read_text(encoding="utf-8")
    head = text.splitlines()[:10]
    joined = "\n".join(head)
    assert "version = " in joined, (
        f"uv.lock missing header; first 10 lines: {joined!r}"
    )
    assert "requires-python" in joined, (
        "uv.lock missing requires-python pin"
    )


def test_uv_lock_has_packages() -> None:
    text = (REPO_ROOT / "uv.lock").read_text(encoding="utf-8")
    package_blocks = text.count("\n[[package]]")
    assert package_blocks >= 10, (
        f"uv.lock should pin ≥10 packages, found {package_blocks}"
    )


def test_security_workflow_present() -> None:
    path = REPO_ROOT / ".github" / "workflows" / "security.yml"
    assert path.is_file(), f"Expected security workflow at {path}"
    text = path.read_text(encoding="utf-8")
    assert "pip-audit" in text
    assert "cyclonedx" in text.lower()


def test_actionlint_workflow_present() -> None:
    path = REPO_ROOT / ".github" / "workflows" / "actionlint.yml"
    assert path.is_file(), f"Expected actionlint workflow at {path}"
    assert "actionlint" in path.read_text(encoding="utf-8")


def test_version_gate_workflow_present() -> None:
    path = REPO_ROOT / ".github" / "workflows" / "version-gate.yml"
    assert path.is_file(), f"Expected version-gate workflow at {path}"
    text = path.read_text(encoding="utf-8")
    assert "CHANGELOG" in text
    assert "VERSION" in text


def test_dependabot_config_present() -> None:
    path = REPO_ROOT / ".github" / "dependabot.yml"
    assert path.is_file(), f"Expected dependabot config at {path}"
    text = path.read_text(encoding="utf-8")
    assert "pip" in text
    assert "github-actions" in text
