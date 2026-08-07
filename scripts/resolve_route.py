#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.loadoutlib import load_loadouts, resolve_loadout_name


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve a Hermes terminal loadout from an operator request.")
    parser.add_argument("--runtime", required=True, choices=["claude", "codex"])
    parser.add_argument("--request", required=True)
    parser.add_argument("--explicit-loadout")
    args = parser.parse_args()

    repo_root = ROOT
    loadouts = load_loadouts(repo_root)
    result = resolve_loadout_name(
        loadouts=loadouts,
        runtime=args.runtime,
        request_text=args.request,
        explicit_loadout=args.explicit_loadout,
    )
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
