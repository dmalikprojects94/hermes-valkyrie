#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.loadoutlib import load_loadouts, validate_loadouts


def main() -> int:
    repo_root = ROOT
    loadouts = load_loadouts(repo_root)
    errors = validate_loadouts(loadouts=loadouts, repo_root=repo_root)
    if errors:
        for error in errors:
            print(error)
        return 1
    print("loadouts valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
