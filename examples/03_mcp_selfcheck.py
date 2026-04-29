#!/usr/bin/env python3
"""Example: call the bundled MCP selfcheck server via in-process transport.

Run from the repo root:
    PYTHONPATH=./scripts python examples/03_mcp_selfcheck.py
"""
from vibecodekit.mcp_servers.selfcheck import ping, echo, now

if __name__ == "__main__":
    print("MCP Selfcheck Server (in-process transport)\n")

    result = ping()
    print(f"  ping()  → {result}")

    result = echo(msg="hello from example")
    print(f"  echo()  → {result}")

    result = now()
    print(f"  now()   → {result}")

    print("\nAll MCP calls succeeded.")
