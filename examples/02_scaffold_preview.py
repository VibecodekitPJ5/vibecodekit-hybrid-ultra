#!/usr/bin/env python3
"""Example: preview all scaffold presets without writing any files.

Run from the repo root:
    PYTHONPATH=./scripts python examples/02_scaffold_preview.py
"""
from vibecodekit.scaffold_engine import ScaffoldEngine

if __name__ == "__main__":
    engine = ScaffoldEngine()
    presets = engine.list_presets()

    print(f"Available presets: {len(presets)}\n")
    for preset in presets:
        stacks = ", ".join(preset.stacks)
        print(f"  {preset.name:<20s} stacks=[{stacks}]")
        print(f"  {'':20s} {preset.description}")

        for stack in preset.stacks:
            plan = engine.preview(preset.name, stack=stack)
            files = [sf.rel_path for sf in plan.files]
            print(f"  {'':20s} [{stack}] {len(files)} files, ~{plan.estimated_loc} LOC")
            for f in files:
                print(f"  {'':24s} {f}")
        print()
