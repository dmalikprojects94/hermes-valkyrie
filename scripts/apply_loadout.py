#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.loadoutlib import apply_loadout, load_loadouts, resolve_loadout_name


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply a Hermes terminal loadout to Claude or Codex.")
    parser.add_argument("--runtime", required=True, choices=["claude", "codex"])
    parser.add_argument("--loadout", help="Explicit loadout name or alias.")
    parser.add_argument("--request", help="Operator request text to resolve into a loadout.")
    parser.add_argument("--output-root", default="output")
    parser.add_argument("--cwd", help="Optional working directory label for launch-status output.")
    parser.add_argument("--target-home", action="store_true", help="Write directly into the provided output-root as a live runtime home.")
    parser.add_argument("--format", choices=["banner", "json", "path"], default="banner")
    args = parser.parse_args()

    repo_root = ROOT
    loadouts = load_loadouts(repo_root)
    loadout_name = args.loadout
    if not loadout_name:
        if not args.request:
            raise SystemExit("Pass --loadout or --request")
        loadout_name = resolve_loadout_name(loadouts=loadouts, runtime=args.runtime, request_text=args.request)

    result = apply_loadout(
        repo_root=repo_root,
        loadouts=loadouts,
        runtime=args.runtime,
        loadout_name=loadout_name,
        output_root=Path(args.output_root),
        target_home=args.target_home,
        cwd=args.cwd,
    )
    if args.format == "json":
        print(json.dumps(result, indent=2))
    elif args.format == "path":
        print(result["output_root"])
    else:
        print(result["launch_notice"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
