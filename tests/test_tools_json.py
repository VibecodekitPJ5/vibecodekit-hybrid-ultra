"""Tests for ``tools.json`` generation and schema validity.

Covers:
- Generator produces valid output
- All tools have inputSchema with type=object
- MCP, CLI, and slash command types are present
- Tool count matches expectations
- tools.json file is in sync with generator output
"""
import json
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_TOOLS_JSON = _REPO / "tools.json"


@pytest.fixture(scope="module")
def tools_data():
    assert _TOOLS_JSON.exists(), "tools.json not found — run: PYTHONPATH=./scripts python tools/gen_tools_json.py"
    return json.loads(_TOOLS_JSON.read_text(encoding="utf-8"))


def test_tools_json_has_schema_key(tools_data):
    assert "$schema" in tools_data


def test_tools_json_has_version(tools_data):
    assert "version" in tools_data
    assert tools_data["version"]  # not empty


def test_tools_json_has_tools_array(tools_data):
    assert "tools" in tools_data
    assert isinstance(tools_data["tools"], list)
    assert len(tools_data["tools"]) > 0


def test_all_tools_have_input_schema(tools_data):
    for tool in tools_data["tools"]:
        assert "inputSchema" in tool, f"{tool['name']} missing inputSchema"
        assert tool["inputSchema"]["type"] == "object", f"{tool['name']} schema type not object"


def test_all_tools_have_name_and_type(tools_data):
    for tool in tools_data["tools"]:
        assert "name" in tool, f"Tool missing name: {tool}"
        assert "type" in tool, f"{tool['name']} missing type"
        assert tool["type"] in {"mcp_tool", "cli", "slash_command"}, \
            f"{tool['name']} has invalid type: {tool['type']}"


def test_mcp_tools_present(tools_data):
    mcp = [t for t in tools_data["tools"] if t["type"] == "mcp_tool"]
    assert len(mcp) == 12
    names = {t["name"] for t in mcp}
    assert "permission_classify" in names
    assert "scaffold_list" in names
    assert "intent_classify" in names


def test_cli_subcommands_present(tools_data):
    cli = [t for t in tools_data["tools"] if t["type"] == "cli"]
    assert len(cli) >= 10
    names = {t["name"] for t in cli}
    assert "vibe audit" in names
    assert "vibe demo" in names
    assert "vibe permission" in names


def test_slash_commands_present(tools_data):
    slash = [t for t in tools_data["tools"] if t["type"] == "slash_command"]
    assert len(slash) >= 42
    names = {t["name"] for t in slash}
    assert "/vibe-run" in names
    assert "/vibe-audit" in names
    assert "/vck-review" in names


def test_all_tools_have_invoke(tools_data):
    for tool in tools_data["tools"]:
        assert "invoke" in tool, f"{tool['name']} missing invoke"


def test_tools_json_is_in_sync_with_generator():
    """Ensure tools.json matches what the generator would produce."""
    import sys
    sys.path.insert(0, str(_REPO / "scripts"))
    from importlib import import_module
    spec = import_module("importlib").util.spec_from_file_location(
        "gen_tools_json", str(_REPO / "tools" / "gen_tools_json.py"))
    mod = import_module("importlib").util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    generated = mod.generate()
    on_disk = json.loads(_TOOLS_JSON.read_text(encoding="utf-8"))
    assert generated["tools"] == on_disk["tools"], \
        "tools.json is out of sync — regenerate with: PYTHONPATH=./scripts python tools/gen_tools_json.py"
