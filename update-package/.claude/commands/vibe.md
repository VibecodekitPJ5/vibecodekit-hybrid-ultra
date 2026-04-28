---
description: Single-prompt master router — type free-form prose to dispatch to the right /vibe-* command
version: 0.11.3
allowed-tools: [Bash, Read]
---

# /vibe

The friendly entrypoint.  Type a free-form prose request in **Vietnamese
or English** and the router will resolve it to one (or more) of the 25
flat `/vibe-*` commands.  All flat commands stay 100 % backward-compatible
— power users can keep using them directly.

## Usage

```bash
# Free-form Vietnamese
/vibe làm cho tôi shop online bán cà phê

# Free-form English
/vibe build a landing page for my coffee shop

# Pipeline expansion
/vibe ra mắt sản phẩm landing page mới

# Single-intent
/vibe audit chất lượng code
/vibe deploy lên Vercel production
/vibe fix lỗi npm peer-deps
/vibe tư vấn kiến trúc microservices
```

## How it routes

The router applies a **hybrid** strategy:

1. **Pipeline triggers** — high-level goals like `"shop online"`,
   `"landing page"`, `"ra mắt sản phẩm"` expand to the canonical
   pipeline `SCAN → VISION → RRI → BUILD → VERIFY`.
2. **Tier-1 keyword scoring** — 14 intents (SCAN / VISION / RRI / RRI-T
   / RRI-UX / RRI-UI / BUILD / VERIFY / SHIP / MAINTAIN / ADVISOR /
   MEMORY / DOCTOR / DASHBOARD), each with VN + EN trigger phrases
   including diacritics-stripped variants (`loi roi fix giup`).
3. **Multi-intent expansion** — multiple intents above the high-conf
   threshold fan out to a sequence of commands in canonical order.
4. **Clarification fallback** — under the low-conf threshold the router
   asks 1 clarifying question (VN + EN) with 4 suggested intents.

## Programmatic API

```bash
python -m vibecodekit.cli intent classify "làm shop online"
python -m vibecodekit.cli intent route    "deploy to Vercel"
```

```python
from vibecodekit.intent_router import IntentRouter
r = IntentRouter()
match = r.classify("làm cho tôi shop online")
print(r.route(match))   # ['/vibe-scan', '/vibe-vision', '/vibe-rri', '/vibe-scaffold', '/vibe-verify']
print(r.explain(match)) # 'Đã hiểu ý bạn (95% chắc chắn). Sẽ chạy: …'
```

## Examples

| Prose | Routed to |
|---|---|
| `phân tích nhu cầu` | `/vibe-scan` |
| `xem tầm nhìn` | `/vibe-vision` |
| `audit chất lượng code` | `/vibe-verify` |
| `deploy lên production` | `/vibe-ship` |
| `scaffold landing page` | `/vibe-scaffold` |
| `nâng cấp Next.js 15` | `/vibe-task` |
| `tư vấn kiến trúc` | `/vibe-tip` |
| `update CLAUDE.md` | `/vibe-memory` |
| `chẩn đoán môi trường` | `/vibe-doctor` |
| `xem dashboard` | `/vibe-dashboard` |

See `USAGE_GUIDE.md` §16.1 for the full keyword table and `IntentRouter` Python API.

## References

- `ai-rules/vibecodekit/references/00-overview.md`
- `ai-rules/vibecodekit/references/30-vibecode-master.md`
