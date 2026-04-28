---
description: "Real-browser QA — chỉ chạy checklist, không fix loop (CI / pre-merge gate)"
version: 0.12.0
allowed-tools: [Bash, Read]
inspired-by: "gstack/qa/SKILL.md.tmpl @ commit 675717e3"
license: "MIT — see LICENSE-third-party.md"
---

# /vck-qa-only — QA without fix loop

Phiên bản chỉ-đọc của `/vck-qa`. Dùng cho:
- CI step: `python -m vibecodekit.cli qa --only --url $STAGING_URL`
- Pre-merge gate trong `/vck-ship`
- Manual smoke test khi không muốn skill auto-edit code

Không có fix loop, không apply diff. Output cùng format như `/vck-qa` nhưng exit code khác:
- `0` — GREEN (pass 12/12)
- `1` — YELLOW (pass ≥ 9/12)
- `2` — RED (pass < 9/12)

Xem `/vck-qa` cho checklist đầy đủ và mô tả checklist VN-12.

> Skill này được port + Việt-hoá từ [gstack/qa](https://github.com/garrytan/gstack/tree/main/qa) (© Garry Tan, MIT). Xem `LICENSE-third-party.md`.
