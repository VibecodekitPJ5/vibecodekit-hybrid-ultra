"""CI guard: chặn ``ALLOWED_ORGS`` phình.

VibecodeKit đã trải qua một chuỗi đổi tên / đổi org (PJ → PJ2 → PJ3 →
mirror PJ4) cộng với 2 attribution upstream (``garrytan`` cho
``gstack``, ``VagabondKingsman`` cho ``taw-kit``).  Tổng cộng **3**
org là số tối đa hợp lý; mọi đề xuất thêm org thứ 4 phải:

1. Mở PR riêng dành cho việc đổi canonical (không gộp với feature).
2. Cập nhật comment block ở đầu ``tests/test_repo_urls_canonical.py``
   giải thích lý do org mới khác mục đích với 3 entry hiện có.
3. Bump giới hạn ở test này và viết lý do trong PR body.

Test này tồn tại để chặn drift "vô tình" — ví dụ ai đó add fork mới
vì redirect tạm rồi quên gỡ.
"""
from __future__ import annotations

from tests.test_repo_urls_canonical import ALLOWED_ORGS

# Soft cap = 3 (PJ3 canonical + garrytan + VagabondKingsman).  Đổi
# số này phải đi kèm comment giải thích trong PR body.
_MAX_ALLOWED_ORGS = 3


def test_allowed_orgs_size_cap():
    assert len(ALLOWED_ORGS) <= _MAX_ALLOWED_ORGS, (
        f"ALLOWED_ORGS đang chứa {len(ALLOWED_ORGS)} entry "
        f"({sorted(ALLOWED_ORGS)}); soft cap là {_MAX_ALLOWED_ORGS}.\n"
        "Trước khi bump cap, đảm bảo:\n"
        "  1. PR riêng cho việc đổi canonical org (không gộp feature).\n"
        "  2. Comment block đầu test_repo_urls_canonical.py giải thích\n"
        "     mục đích của entry mới (không phải duplicate của entry cũ).\n"
        "  3. PR body có lý do ngắn gọn vì sao bump cap."
    )


def test_allowed_orgs_are_strings():
    """Sanity check — phòng khi ai đó tự rename trong PR feature."""
    for org in ALLOWED_ORGS:
        assert isinstance(org, str) and "/" not in org, (
            f"ALLOWED_ORGS chỉ nên chứa tên org thuần (không slash): {org!r}"
        )
