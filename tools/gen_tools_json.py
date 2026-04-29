#!/usr/bin/env python3
"""Generate ``tools.json`` — machine-readable JSON Schema for every
vibecodekit entry point (MCP tools, CLI subcommands, slash commands).

Run from repo root::

    PYTHONPATH=./scripts python tools/gen_tools_json.py

Output is written to ``tools.json`` (repo root).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List


def _mcp_tools() -> List[Dict[str, Any]]:
    """Extract schemas from the MCP core server registry."""
    from vibecodekit.mcp_servers.core import _TOOLS

    out = []
    for name, meta in _TOOLS.items():
        out.append({
            "name": name,
            "type": "mcp_tool",
            "transport": ["stdio", "inproc"],
            "description": meta["description"],
            "inputSchema": meta["inputSchema"],
            "invoke": {
                "stdio": f"python -m vibecodekit.mcp_servers.core  # tools/call {name}",
                "inproc": f"from vibecodekit.mcp_servers.core import {name}",
            },
        })
    return out


def _cli_subcommands() -> List[Dict[str, Any]]:
    """Hand-curated schemas for CLI subcommands.

    We don't introspect argparse at runtime because the parser tree is
    built inside ``_build_parser()`` which has side-effects.  Instead we
    maintain a curated list of the most-used subcommands with their
    argument schemas.
    """
    return [
        {
            "name": "vibe run",
            "type": "cli",
            "description": "Execute a query-loop plan",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan": {"type": "string", "description": "Plan file or inline plan"},
                    "--mode": {"type": "string", "enum": ["default", "plan", "accept_edits", "bypass", "auto", "bubble"], "default": "default"},
                    "--root": {"type": "string", "default": "."},
                },
                "required": ["plan"],
            },
            "invoke": {"cli": "vibe run <plan> [--mode default] [--root .]"},
        },
        {
            "name": "vibe doctor",
            "type": "cli",
            "description": "Health-check a vibecode project layout",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "--installed-only": {"type": "boolean", "default": False},
                    "--root": {"type": "string", "default": "."},
                },
            },
            "invoke": {"cli": "vibe doctor [--installed-only] [--root .]"},
        },
        {
            "name": "vibe audit",
            "type": "cli",
            "description": "Run conformance audit (87 probes)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "--threshold": {"type": "number", "default": 0.85, "minimum": 0, "maximum": 1},
                    "--json": {"type": "boolean", "default": False, "description": "Output JSON instead of human-readable table"},
                    "--root": {"type": "string", "default": "."},
                },
            },
            "invoke": {"cli": "vibe audit [--threshold 0.85] [--json] [--root .]"},
        },
        {
            "name": "vibe permission",
            "type": "cli",
            "description": "Classify a command through the 6-layer permission pipeline",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to classify"},
                    "--mode": {"type": "string", "enum": ["default", "plan", "accept_edits", "bypass", "auto", "bubble"], "default": "default"},
                    "--unsafe": {"type": "boolean", "default": False},
                    "--root": {"type": "string", "default": "."},
                },
                "required": ["command"],
            },
            "invoke": {"cli": "vibe permission <command> [--mode default] [--root .]"},
        },
        {
            "name": "vibe install",
            "type": "cli",
            "description": "Install vibecodekit overlay into a project",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "destination": {"type": "string", "description": "Target project directory"},
                    "--dry-run": {"type": "boolean", "default": False},
                    "--root": {"type": "string", "default": "."},
                },
                "required": ["destination"],
            },
            "invoke": {"cli": "vibe install <destination> [--dry-run] [--root .]"},
        },
        {
            "name": "vibe discover",
            "type": "cli",
            "description": "Dynamic skill discovery",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "--touched": {"type": "string", "default": None, "description": "File path to check for skill activation"},
                    "--root": {"type": "string", "default": "."},
                },
            },
            "invoke": {"cli": "vibe discover [--touched <path>] [--root .]"},
        },
        {
            "name": "vibe scaffold",
            "type": "cli",
            "description": "Scaffold a project from a preset",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Output directory"},
                    "--root": {"type": "string", "default": "."},
                },
                "required": ["path"],
            },
            "invoke": {"cli": "vibe scaffold <path> [--root .]"},
        },
        {
            "name": "vibe compact",
            "type": "cli",
            "description": "5-layer context compaction",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "--reactive": {"type": "boolean", "default": False},
                    "--root": {"type": "string", "default": "."},
                },
            },
            "invoke": {"cli": "vibe compact [--reactive] [--root .]"},
        },
        {
            "name": "vibe intent",
            "type": "cli",
            "description": "Classify free-form prose to slash commands",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "--json": {"type": "boolean", "default": False},
                    "--root": {"type": "string", "default": "."},
                },
            },
            "invoke": {"cli": "vibe intent [--json] [--root .]"},
        },
        {
            "name": "vibe dashboard",
            "type": "cli",
            "description": "Runtime event summary",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "--root": {"type": "string", "default": "."},
                },
            },
            "invoke": {"cli": "vibe dashboard [--root .]"},
        },
        {
            "name": "vibe demo",
            "type": "cli",
            "description": "Run interactive demo showcasing core capabilities (< 2s, zero network)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "--root": {"type": "string", "default": "."},
                },
            },
            "invoke": {"cli": "vibe demo [--root .]"},
        },
        {
            "name": "vibe memory retrieve",
            "type": "cli",
            "description": "Retrieve from 3-tier memory hierarchy",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "--top-k": {"type": "integer", "default": 8},
                    "--backend": {"type": "string", "default": None},
                    "--tiers": {"type": "array", "items": {"type": "string"}, "default": None},
                    "--root": {"type": "string", "default": "."},
                },
                "required": ["query"],
            },
            "invoke": {"cli": "vibe memory retrieve <query> [--top-k 8] [--root .]"},
        },
        {
            "name": "vibe memory add",
            "type": "cli",
            "description": "Add entry to a memory tier",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tier": {"type": "string", "enum": ["user", "team", "project"]},
                    "text": {"type": "string"},
                    "--header": {"type": "string", "default": "(entry)"},
                    "--source": {"type": "string", "default": "log.jsonl"},
                    "--root": {"type": "string", "default": "."},
                },
                "required": ["tier", "text"],
            },
            "invoke": {"cli": "vibe memory add <tier> <text> [--header (entry)] [--root .]"},
        },
        {
            "name": "vibe config show",
            "type": "cli",
            "description": "Show current configuration",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "--root": {"type": "string", "default": "."},
                },
            },
            "invoke": {"cli": "vibe config show [--root .]"},
        },
        {
            "name": "vibe config set-backend",
            "type": "cli",
            "description": "Set embedding backend (hash-256, sentence-transformers)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "backend": {"type": "string", "enum": ["hash-256", "sentence-transformers"]},
                    "--root": {"type": "string", "default": "."},
                },
                "required": ["backend"],
            },
            "invoke": {"cli": "vibe config set-backend <backend> [--root .]"},
        },
    ]


def _slash_commands() -> List[Dict[str, Any]]:
    """Extract slash command metadata from manifest.llm.json."""
    manifest_path = Path(__file__).resolve().parent.parent / "manifest.llm.json"
    if not manifest_path.exists():
        return []
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    out = []
    for cmd in data.get("commands", []):
        out.append({
            "name": "/" + cmd["name"],
            "type": "slash_command",
            "description": f"Slash command — see {cmd['file']}",
            "file": cmd["file"],
            "inputSchema": {
                "type": "object",
                "properties": {
                    "args": {"type": "string", "description": "Free-form arguments passed after the command name"},
                },
            },
            "invoke": {"slash": f"/{cmd['name']} [args]"},
        })
    return out


def generate() -> Dict[str, Any]:
    """Build the full tools.json structure."""
    from vibecodekit import VERSION
    return {
        "$schema": "https://vibecodekit.dev/schema/tools-0.1.json",
        "name": "vibecodekit-hybrid-ultra",
        "version": VERSION,
        "generated_by": "tools/gen_tools_json.py",
        "tools": _mcp_tools() + _cli_subcommands() + _slash_commands(),
    }


def main() -> int:
    doc = generate()
    out_path = Path(__file__).resolve().parent.parent / "tools.json"
    out_path.write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"tools.json: {len(doc['tools'])} tools written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
