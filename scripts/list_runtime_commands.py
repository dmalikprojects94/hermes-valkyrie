#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.loadoutlib import (  # noqa: E402
    _command_inventory,
    _render_command_inventory_markdown,
    load_loadouts,
    resolve_loadout,
    resolve_loadout_name,
)


def _inventory_for(loadouts: dict, *, runtime: str, loadout_name: str | None, request: str | None) -> dict:
    resolved_name = loadout_name
    if not resolved_name:
        if not request:
            raise SystemExit("Pass --loadout or --request")
        resolved_name = resolve_loadout_name(loadouts=loadouts, runtime=runtime, request_text=request)
    resolved = resolve_loadout(loadouts, resolved_name)
    if runtime not in resolved.get("supported_runtimes", []):
        raise SystemExit(f"Loadout {resolved_name} does not support runtime {runtime}")
    return _command_inventory(ROOT, resolved, runtime)


def _command_map(inventory: dict) -> dict[str, dict]:
    return {entry["name"]: entry for entry in inventory.get("commands", [])}


def _compare_inventories(*, claude: dict, codex: dict) -> dict:
    claude_map = _command_map(claude)
    codex_map = _command_map(codex)
    shared = sorted(set(claude_map) & set(codex_map))
    claude_only = sorted(set(claude_map) - set(codex_map))
    codex_only = sorted(set(codex_map) - set(claude_map))
    return {
        "schema_version": 1,
        "loadout": claude.get("loadout") or codex.get("loadout"),
        "runtimes": {"claude": claude, "codex": codex},
        "summary": {
            "claude_count": len(claude_map),
            "codex_count": len(codex_map),
            "shared_exact_name_count": len(shared),
            "claude_only_count": len(claude_only),
            "codex_only_count": len(codex_only),
        },
        "shared_exact_names": shared,
        "claude_only": [claude_map[name] for name in claude_only],
        "codex_only": [codex_map[name] for name in codex_only],
        "note": "Exact-name parity is mechanical. Treat runtime-native commands and Hermes-managed skill triggers as intentional gaps unless a loadout contract says otherwise.",
    }


def _render_compare_markdown(compare: dict) -> str:
    summary = compare["summary"]
    lines = [
        f"# Runtime command parity — {compare['loadout']}",
        "",
        f"Claude commands: {summary['claude_count']}",
        f"Codex commands/command-equivalent skills: {summary['codex_count']}",
        f"Shared exact names: {summary['shared_exact_name_count']}",
        f"Claude-only: {summary['claude_only_count']}",
        f"Codex-only: {summary['codex_only_count']}",
        "",
        compare["note"],
        "",
        "## Shared exact names",
        "",
    ]
    lines.extend(f"- `{name}`" for name in compare["shared_exact_names"])
    lines.extend(["", "## Claude-only", ""])
    lines.extend(f"- `{entry['invocation']}` — {entry.get('title', entry['name'])}" for entry in compare["claude_only"])
    lines.extend(["", "## Codex-only", ""])
    lines.extend(f"- `{entry['invocation']}` — {entry.get('title', entry['name'])} ({entry.get('kind', '')})" for entry in compare["codex_only"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="List slash commands and command-equivalent skills for a Hermes terminal loadout.")
    parser.add_argument("--runtime", choices=["claude", "codex"], help="Runtime to inspect. Omit with --compare to compare Claude and Codex.")
    parser.add_argument("--compare", action="store_true", help="Compare Claude and Codex command inventories for the selected loadout/request.")
    parser.add_argument("--loadout", help="Explicit loadout name or alias.")
    parser.add_argument("--request", help="Resolve the loadout from an operator request instead of --loadout.")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    args = parser.parse_args()

    loadouts = load_loadouts(ROOT)
    if args.compare:
        claude = _inventory_for(loadouts, runtime="claude", loadout_name=args.loadout, request=args.request)
        codex = _inventory_for(loadouts, runtime="codex", loadout_name=args.loadout, request=args.request)
        compare = _compare_inventories(claude=claude, codex=codex)
        if args.format == "json":
            print(json.dumps(compare, indent=2))
        else:
            print(_render_compare_markdown(compare), end="")
        return 0
    if not args.runtime:
        raise SystemExit("Pass --runtime, or pass --compare to compare both runtimes")
    inventory = _inventory_for(loadouts, runtime=args.runtime, loadout_name=args.loadout, request=args.request)
    if args.format == "json":
        print(json.dumps(inventory, indent=2))
    else:
        print(_render_command_inventory_markdown(inventory))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
