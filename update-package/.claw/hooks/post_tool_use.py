#!/usr/bin/env python3
"""post_tool_use hook — appends the result summary to the session event bus."""
import json, os, sys
payload = json.loads(os.environ.get("VIBECODE_HOOK_PAYLOAD", "{}") or "{}")
sys.stdout.write(json.dumps({"decision": "allow", "observed_tool": payload.get("tool")}))
