#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOADOUT="${1:-default}"
OUTPUT_ROOT="${2:-$HOME/.codex}"
python "$ROOT/scripts/apply_loadout.py" --runtime codex --loadout "$LOADOUT" --output-root "$OUTPUT_ROOT" --target-home
