# Examples

Standalone scripts demonstrating core VibecodeKit capabilities.
**No network, no LLM, no Claude Code required.**

## Quick start

```bash
git clone https://github.com/VibecodekitPJ3/vibecodekit-hybrid-ultra.git
cd vibecodekit-hybrid-ultra

# All-in-one demo (< 2 seconds):
PYTHONPATH=./scripts python -m vibecodekit.cli demo

# Or run individual examples:
PYTHONPATH=./scripts python examples/01_permission_engine.py
PYTHONPATH=./scripts python examples/02_scaffold_preview.py
PYTHONPATH=./scripts python examples/03_mcp_selfcheck.py
```

## What each example does

| Script | Description |
|--------|-------------|
| `01_permission_engine.py` | Classify 20 shell commands through the 6-layer permission pipeline |
| `02_scaffold_preview.py` | List and preview all 10 scaffold presets across available stacks |
| `03_mcp_selfcheck.py` | Call the bundled MCP selfcheck server via in-process transport |

## All-in-one demo

`vibe demo` runs 6 steps in sequence:

1. **Doctor** — health-check the project layout
2. **Permission Engine** — classify 5 commands (allow/deny)
3. **Conformance Audit** — run 87 internal regression probes
4. **Scaffold Preview** — preview the `api-todo` preset
5. **Intent Router** — classify 3 free-form phrases to slash commands
6. **MCP Selfcheck** — ping the bundled MCP server
