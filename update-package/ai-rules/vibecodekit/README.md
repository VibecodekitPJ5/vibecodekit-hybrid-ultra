# ai-rules/vibecodekit/ — runtime landing zone

This directory is populated by the reconciliation installer. The installer
itself lives in the skill bundle, not in this update package — so you must
extract the skill bundle first and run the installer from there:

```bash
# Extract skill bundle (contains runtime scripts + installer)
unzip vibecodekit-hybrid-ultra-v0.11.2-skill.zip -d ~/.vibecode

# Run installer with PYTHONPATH pointing at the skill bundle's scripts/
PYTHONPATH=~/.vibecode/vibecodekit-hybrid-ultra/scripts \
  python -m vibecodekit.cli install /path/to/myproject
```

Note: Do **not** try `python -m ai-rules.vibecodekit.scripts.vibecodekit.cli …`
— hyphens are not allowed in Python module paths, and this sub-directory is
empty until the installer has run.

After install you will find:

- `scripts/vibecodekit/` — the runtime Python package (imported as
  `vibecodekit.*`)
- `references/` — the 18-pattern + methodology markdown references
- `templates/` — TIP / verify / completion / blueprint / scan / conformance
  templates
- `SKILL.md` — the activation contract for agents

The update package ships those four sub-directories empty; the installer
copies them from the skill bundle in an idempotent, hash-diffed fashion
(Pattern #16).

## Why is this sub-directory empty in the update package?

Shipping the full payload *and* the installer would double the footprint
and risk drift between the two copies (exactly the v0.6 defect).  The
update package contains **only the parts that must live in the project
tree**: slash commands, agent cards, hooks, and a placeholder README.
The runtime package itself is pulled from the skill bundle at install
time.
