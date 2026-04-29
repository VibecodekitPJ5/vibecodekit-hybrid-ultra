# VibecodeKit Hybrid Ultra — 5-minute Quickstart

> Nếu bạn chưa biết bộ kit này là gì — nó là một **Agentic OS** cho các
> CLI lập trình (ChatGPT, Claude Code / Claw Code, Codex, Cursor) giúp biến
> một dự án "mơ hồ" thành một pipeline 8 bước đo được.  Bản này cho bạn
> khởi động trong 5 phút, không cần đọc hết 960 dòng `USAGE_GUIDE.md`.

---

## Bước 0 — Bạn là ai?

| Vai trò | Mô tả | Đi con đường nào |
|--------|-------|------------------|
| 🏠 **Chủ nhà** | Bạn muốn ra tính năng, không quan tâm code | **Con đường A — ChatGPT-only** |
| 📋 **Chủ thầu** | Bạn review/spec, không gõ code ngày nào | **Con đường B — ChatGPT + 1 CLI** |
| 🔨 **Thợ** | Bạn thực sự viết code | **Con đường C — Claude/Claw/Codex CLI** |

---

## Con đường A — ChatGPT-only (0 cài đặt)

1. Tải file `vibecodekit-hybrid-ultra-vX.Y.Z-skill.zip`.
2. Mở một ChatGPT conversation mới (GPT-4/4o/5).
3. Kéo–thả file zip vào khung chat.
4. Gửi tin nhắn:

   ```
   Bạn là "Chủ thầu" trong hệ VIBECODE-MASTER. Tôi đính kèm skill
   bundle vibecodekit-hybrid-ultra vX.Y.Z. Hãy giải nén, đọc SKILL.md,
   reference 29 (RRI), 30 (VIBECODE-MASTER). Sau đó chạy /vibe-scan cho dự án:

   "<mô tả dự án 2-3 câu>"
   ```

5. Sau khi ChatGPT trả scan report, gõ tiếp `/vibe-rri CHALLENGE` →
   `/vibe-vision` → `/vibe-blueprint` → `/vibe-task graph`.

Bạn đã xong "phần thiết kế" của dự án mà chưa phải mở terminal.  Export
kết quả về `.md` rồi giao cho dev thực thi.

---

## Con đường B — ChatGPT + CLI methodology (5 phút cài)

Dùng khi bạn muốn chạy release gate (RRI-T / RRI-UX / VN checklist) thực
tế trên máy mình.

```bash
# 1. Giải nén
unzip vibecodekit-hybrid-ultra-vX.Y.Z-skill.zip -d ~/.vibecode/

# 2. Xuất PYTHONPATH (thêm vào ~/.bashrc / ~/.zshrc để không phải gõ lại)
export PYTHONPATH=~/.vibecode/vibecodekit-hybrid-ultra/scripts

# 3. Test thử một lệnh
python -m vibecodekit.cli audit
# → kỳ vọng: 87/87 probes pass (internal self-test, not external benchmark)
```

Dùng `vibe rri-t reports/testing.jsonl` sau mỗi sprint để kiểm tra cổng
release.  Format JSONL xem `USAGE_GUIDE.md §8`.

---

## Con đường C — Claude Code / Claw Code / Codex CLI (10 phút)

```bash
# 1. Giải nén update-package vào thư mục dự án (KHÔNG phải home)
cd <my-project>
unzip ~/Downloads/vibecodekit-hybrid-ultra-vX.Y.Z-update-package.zip -d .

# 2. Nếu dùng Claude Code / Claw Code:
claude-code
> /vibe-doctor    # sanity check
> /vibe-scan      # start pipeline

# 3. Nếu dùng Codex CLI:
codex --system-file ai-rules/vibecodekit/SKILL.md "/vibe-scan"

# 4. Nếu dùng Cursor:
# Update-package có sẵn `.claude/commands/*.md` — Cursor tự nhận.
# Hoặc chuyển sang `.cursor/rules/` bằng script nhỏ, xem USAGE_GUIDE §2.2
```

Bạn sẽ thấy ngay 42 slash command mới (25 `/vibe-*` + 1 master `/vibe` + 16 `/vck-*`): `/vibe-scan`, `/vibe-scaffold`, `/vibe-ship`,
`/vibe-blueprint`, ..., `/vibe-audit`.

---

## Kiểm chứng bộ kit hoạt động đúng

```bash
# 1. Unit test runtime
cd ~/.vibecode/vibecodekit-hybrid-ultra
pytest tests/ -q        # → all actionable tests pass

# 2. Conformance self-test (internal regression guard — see BENCHMARKS-METHODOLOGY.md)
PYTHONPATH=scripts python -m vibecodekit.conformance_audit
# → 87/87 probes pass (internal self-test)

# 3. Permission engine (phải chặn lệnh nguy hiểm)
PYTHONPATH=scripts python -m vibecodekit.cli permission "rm -rf /"
# → {"decision": "deny", "reason": "destructive recursive delete"}

# 4. Methodology gate
echo '{"id":"x","dimension":"D1","result":"PASS","priority":"P1"}' > t.jsonl
for d in D2 D3 D4 D5 D6 D7; do
  echo "{\"id\":\"$d\",\"dimension\":\"$d\",\"result\":\"PASS\",\"priority\":\"P1\"}" >> t.jsonl
done
PYTHONPATH=scripts python -m vibecodekit.cli rri-t t.jsonl
# → exit code 0, gate: PASS
```

---

## 3 câu hỏi thường gặp

**Q: Dùng được trên Windows không?**  A: Được.  Kit có sẵn
`_platform_lock.py` dùng `msvcrt.locking()` trên Windows và
`fcntl.flock()` trên Linux/macOS.  Test runtime cần Python 3.9+.

**Q: Semantic search dở quá — có thể dùng embedding xịn không?**
A: Có.  Mặc định là `hash-256` (offline, reproducible, chất lượng trung
bình).  Đổi sang `sentence-transformers`:

```bash
pip install sentence-transformers
PYTHONPATH=scripts python -m vibecodekit.cli config set-backend sentence-transformers
```

**Q: Muốn xem dashboard đẹp thay vì terminal?**  A: Roadmap v0.11 sẽ có
web dashboard.  Tạm thời dùng `vibe dashboard` (terminal) — xuất JSONL
event, có thể grep/jq.

---

## Bước tiếp theo

- Đọc `USAGE_GUIDE.md` — 15 section đầy đủ, 960 dòng.
- Đọc `references/29-rri-reverse-interview.md` — method luận cốt lõi.
- Đọc `references/30-vibecode-master.md` — triết lý 3 vai × 8 bước.
- Chạy `/vibe-audit` → `/vibe-doctor` để chẩn đoán sức khỏe cài đặt.

Có lỗi/góp ý? Mở issue trong repo (nếu có) hoặc ghi log qua
`python -m vibecodekit.cli doctor --installed-only`.
