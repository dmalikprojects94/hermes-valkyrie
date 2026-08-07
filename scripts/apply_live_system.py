#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import pwd
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.loadoutlib import apply_loadout, load_loadouts, resolve_loadout_name, validate_loadouts

def _real_user_home() -> Path:
    override = os.environ.get("HERMES_REAL_HOME") or os.environ.get("REAL_HOME")
    if override:
        return Path(override).expanduser().resolve()
    return Path(pwd.getpwuid(os.getuid()).pw_dir).resolve()


def _live_home_defaults() -> dict[str, Path]:
    real_home = _real_user_home()
    return {
        "claude": real_home / ".claude",
        "codex": real_home / ".codex",
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate this repo and apply a selected loadout directly to a live Claude/Codex home."
    )
    parser.add_argument("--runtime", required=True, choices=sorted(_live_home_defaults()))
    parser.add_argument("--loadout", help="Explicit loadout name or alias.")
    parser.add_argument("--request", help="Operator request text to resolve into a loadout.")
    parser.add_argument("--output-root", help="Override the live runtime home path. Defaults to ~/.claude or ~/.codex.")
    parser.add_argument("--cwd", help="Optional working directory label for launch-status output.")
    parser.add_argument("--format", choices=["banner", "json", "path"], default="banner")
    parser.add_argument("--dry-run", action="store_true", help="Validate and resolve only. Do not write runtime files.")
    parser.add_argument("--yes", action="store_true", help="Required for live writes unless --dry-run is used.")
    return parser.parse_args()


def _resolve_output_root(runtime: str, override: str | None) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    return _live_home_defaults()[runtime].resolve()


def _validate_repo_or_exit(loadouts: dict[str, dict]) -> None:
    errors = validate_loadouts(loadouts=loadouts, repo_root=ROOT)
    if errors:
        joined = "\n".join(f"- {error}" for error in errors)
        raise SystemExit(f"Refusing live apply; loadout validation failed:\n{joined}")


def main() -> int:
    args = _parse_args()
    loadouts = load_loadouts(ROOT)
    _validate_repo_or_exit(loadouts)

    if not args.loadout and not args.request:
        raise SystemExit("Pass --loadout or --request")

    loadout_name = resolve_loadout_name(
        loadouts=loadouts,
        runtime=args.runtime,
        request_text=args.request or args.loadout or "",
        explicit_loadout=args.loadout,
    )
    output_root = _resolve_output_root(args.runtime, args.output_root)

    if args.dry_run:
        result = {
            "runtime": args.runtime,
            "loadout": loadout_name,
            "output_root": str(output_root),
            "target_mode": "live-home",
            "would_write": False,
            "validation": "passed",
        }
    else:
        if not args.yes:
            raise SystemExit(
                "Refusing to write live runtime home without --yes. "
                f"Dry-run first: {Path(__file__).name} --runtime {args.runtime} --loadout {loadout_name} --dry-run"
            )
        if output_root == ROOT or ROOT in output_root.parents:
            raise SystemExit(f"Refusing to apply live home inside source repo: {output_root}")
        result = apply_loadout(
            repo_root=ROOT,
            loadouts=loadouts,
            runtime=args.runtime,
            loadout_name=loadout_name,
            output_root=output_root,
            target_home=True,
            cwd=args.cwd,
        )
        result["validation"] = "passed"
        result["would_write"] = True

    if args.format == "json":
        print(json.dumps(result, indent=2))
    elif args.format == "path":
        print(result["output_root"])
    else:
        if args.dry_run:
            print(f"DRY RUN | {args.runtime.upper()} | loadout: {loadout_name} | target: {output_root}")
        else:
            print(result["launch_notice"])
            print(f"Applied live {args.runtime} home: {result['output_root']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
