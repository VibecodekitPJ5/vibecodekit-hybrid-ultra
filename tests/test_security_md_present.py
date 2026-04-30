"""CI guard cho PR1 — `SECURITY.md` + `.github/CODEOWNERS` phải tồn tại
và có cấu trúc tối thiểu theo layout gstack-style.

Mục đích:
- Đảm bảo enterprise reviewer luôn đọc được SECURITY.md với 6 section
  (Reporting / Supported / Security model / Threat model / Known
  limitations / References) — layout port từ
  ``garrytan/gstack`` ``ARCHITECTURE.md`` "Security model" (clean-room,
  chỉ port pattern).
- Đảm bảo ``.github/CODEOWNERS`` vẫn chỉ định owner cho
  ``permission_engine.py`` — file security-critical nhất của repo.

Test này **không** scan chi tiết nội dung (ví dụ số lượng layer cụ
thể) để tránh drift khi policy tiến hoá; drift về nội dung được xử
lý ở PR4 (permission engine rule list) và PR6/PR7 (coverage / mypy
gate).  Ở đây chỉ guard cấu trúc file.
"""
from __future__ import annotations

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


REQUIRED_SECURITY_SECTIONS = (
    "Reporting a vulnerability",
    "Supported versions",
    "Security model",
    "Threat model",
    "Known limitations",
    "References",
)


def test_security_md_present() -> None:
    path = REPO_ROOT / "SECURITY.md"
    assert path.is_file(), f"Expected SECURITY.md at {path}"


def test_security_md_has_required_sections() -> None:
    text = (REPO_ROOT / "SECURITY.md").read_text(encoding="utf-8")
    # Liệt kê heading level-2 (``## …``).  Chấp nhận suffix tuỳ ý
    # (``## Security model — layered defense``) miễn prefix khớp.
    headings = [
        line[3:].strip()
        for line in text.splitlines()
        if line.startswith("## ")
    ]
    missing = []
    for required in REQUIRED_SECURITY_SECTIONS:
        if not any(h.startswith(required) for h in headings):
            missing.append(required)
    assert not missing, (
        f"SECURITY.md thiếu section bắt buộc: {missing}\n"
        f"Heading hiện có: {headings}"
    )


def test_security_md_minimum_section_count() -> None:
    """Soft guard: ít nhất 6 heading H2 — khớp layout gstack."""
    text = (REPO_ROOT / "SECURITY.md").read_text(encoding="utf-8")
    h2_count = sum(1 for line in text.splitlines() if line.startswith("## "))
    assert h2_count >= len(REQUIRED_SECURITY_SECTIONS), (
        f"SECURITY.md chỉ có {h2_count} heading ``## …`` "
        f"(yêu cầu ≥ {len(REQUIRED_SECURITY_SECTIONS)})."
    )


def test_codeowners_present() -> None:
    path = REPO_ROOT / ".github" / "CODEOWNERS"
    assert path.is_file(), f"Expected .github/CODEOWNERS at {path}"


def test_codeowners_covers_permission_engine() -> None:
    """Security-critical module phải có owner rule explicit."""
    text = (REPO_ROOT / ".github" / "CODEOWNERS").read_text(encoding="utf-8")
    assert "permission_engine.py" in text, (
        "CODEOWNERS phải có rule cho permission_engine.py — file "
        "security-critical nhất của repo."
    )
    # Kiểm tra ít nhất có 1 owner handle (@org/team hoặc @user) trên
    # cùng dòng với permission_engine.py.
    for line in text.splitlines():
        if "permission_engine.py" in line:
            assert "@" in line, (
                f"Rule CODEOWNERS cho permission_engine.py thiếu owner "
                f"handle: {line!r}"
            )
            break
    else:  # pragma: no cover - guard bên trên đã assert tồn tại pattern
        pytest.fail("Không tìm thấy dòng rule cho permission_engine.py")


def test_codeowners_has_default_fallback() -> None:
    """Fallback ``*`` bắt buộc để mọi file đều có owner mặc định."""
    text = (REPO_ROOT / ".github" / "CODEOWNERS").read_text(encoding="utf-8")
    has_default = any(
        line.lstrip().startswith("*") and "@" in line
        for line in text.splitlines()
        if not line.lstrip().startswith("#")
    )
    assert has_default, "CODEOWNERS thiếu rule fallback ``*  @owner`` mặc định."
