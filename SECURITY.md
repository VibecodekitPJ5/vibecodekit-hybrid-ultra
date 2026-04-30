# Security policy

## Reporting a vulnerability
- Private channel: GitHub Security Advisories ở repo này (preferred).
- SLA: ack ≤ 72h, patch hoặc public advisory ≤ 30 ngày kể từ ack.
- KHÔNG submit qua public issue / PR.

## Supported versions
| Version | Status         |
|---------|----------------|
| 0.16.x  | active support |
| < 0.16  | end-of-life    |

## Security model — layered defense

VibecodeKit Hybrid Ultra defends 3 surface:

### Surface 1 — Permission engine (shell command pre-execution)
6-layer pipeline. Mỗi command chạy qua tất cả 6 layer:

| Layer | Cơ chế | Outcome |
|---|---|---|
| L1 | Allowlist match (read-only verb như `git status`, `ls`, `cat`) | allow |
| L2 | Mode check (`plan` blocks all writes) | deny if mode=plan + write op |
| L3 | Rule pattern match (deny patterns: `rm -rf /`, `dd if=/dev/zero of=/dev/sda`, `mkfs`, fork bomb, ...) | deny + audit |
| L4 | Dangerous-pattern AST check (eval/exec wrapping, command substitution `$(...)`) | deny + audit |
| L5 | Cf-codepoint Unicode normalization (170 invisible separator) | normalize then re-evaluate |
| L6 | Denial tracking (rate-cap 60 events/min global, write `~/.vibecodekit/security/attempts.jsonl`) | log + return |

### Surface 2 — Hook interceptor (env / file write scrubbing)
Scrub regex `(TOKEN|KEY|SECRET|PASSWORD|PASSWD|PRIVATE|CREDENTIAL)` trên env var name + value patterns. Override: `VIBECODE_HOOK_ALLOW_SECRETS=1`.

### Surface 3 — MCP tool boundary
Tools registered via `tools.json` chạy qua permission engine trước khi execute shell. ML classifier optional (`pip install vibecodekit-hybrid-ultra[ml]`) cho prompt-injection scan trên user input.

## Threat model

### In scope
- Permission engine bypass (Cf-codepoint, eval wrap, command substitution, compound `&&`/`;`/`|`).
- Secret leak via hook (env propagation to subprocess).
- Path traversal trong `scaffold_engine` + `install_manifest` (verified: `Path.resolve()` everywhere).
- Code injection via `intent_router` user-prompt → command match.
- Audit log tampering / log-flood DoS (rate-cap 60/min mitigates).

### Out of scope
- Network/tunnel surface — VibecodeKit KHÔNG bind public port, không có remote daemon. Khác với gstack browser daemon (có dual-listener tunnel architecture).
- ML/browser optional extras (`[browser]`, `[ml]`) — ngoài core security boundary.
- Downstream user code (kit chỉ cung cấp engine; user app phải tự verify).
- Multi-tenant RBAC — single-agent permission model only ở v0.x. Sẽ thêm nếu enterprise demand.

## Known limitations (v0.16.2)
- Coverage 57% trên `tool_executor.py` (hot-path subprocess) — tăng lên ≥80% ở PR7.
- mypy strict 22 errors trong 4 core file — fix ở PR6.
- Logging: `print()` ad-hoc thay vì `logging` (PR2 fix).
- 4 pattern hiện trả "ask" thay vì "deny" (PR4 fix): `chmod 777 /`, `shutdown`, `history -c`, `rm $(...)`.

## Supply chain & reproducible builds (PR3)

- `uv.lock` (repo root) pin hash + version cho toàn bộ dependency tree
  (83 package resolved cross-platform ở v0.16.2). Contributor muốn
  deterministic env: `uv sync --frozen` (không cập nhật lock).
- CI workflow `.github/workflows/security.yml` chạy `pip-audit --strict`
  trên `uv.lock` (export sang requirements-lock.txt) + sinh CycloneDX
  SBOM (`sbom.json`) cho mỗi PR + lịch weekly Monday 06:00 UTC.
- Artifact `pip-audit` (JSON) và `sbom` (JSON) được upload trên mỗi
  run — reviewer tải về để verify manually.
- Dependabot (`.github/dependabot.yml`) mở tối đa 5 PR/week cho `pip` +
  5 PR/week cho `github-actions` ecosystem (default của Dependabot v2
  khi không set `open-pull-requests-limit`).

## References
- Inspired by `garrytan/gstack` `ARCHITECTURE.md` "Security model" layout,
  `careful/bin/check-careful.sh` (PR4), và `ci-image.yml` / `actionlint.yml`
  / `version-gate.yml` workflow pattern (PR3).
- Cf-codepoint testing: probe 5 codepoint × `rm -rf /` bypass — all denied (verified v0.16.2).
