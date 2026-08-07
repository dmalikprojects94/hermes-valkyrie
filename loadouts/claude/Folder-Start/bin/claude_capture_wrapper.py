#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def default_capture_root() -> Path:
    """Return the capture root without requiring a private save path.

    Public copies must be runnable without operator-specific environment. When
    `SAVE_DESTINATION_PATH` is unset, keep raw capture local to the current
    working tree instead of attempting to create a placeholder absolute path.

    `OBSIDIAN_VAULT_PATH` is accepted as a legacy compatibility alias for
    existing Hermes deployments that already route capture into an Obsidian
    vault.
    """
    explicit = os.environ.get('SAVE_DESTINATION_PATH') or os.environ.get('OBSIDIAN_VAULT_PATH')
    if explicit:
        return Path(explicit)
    return Path.cwd() / 'local-runtime-artifacts' / 'raw-capture'


DEFAULT_VAULT = default_capture_root()
# Agent-scoped raw lane shared with the coding-terminal artifact router.
DEFAULT_AGENT_DIR = Path('agents/claude-code/raw-runs')


def slugify(text: str) -> str:
    value = re.sub(r'[^a-zA-Z0-9]+', '-', text.strip().lower()).strip('-')
    return value or 'claude-run'


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Capture raw and structured Claude Code output into the canonical Obsidian raw lane.')
    parser.add_argument('--project-slug', default='hermes-coding-terminal-load-out-system')
    parser.add_argument('--label', default='claude-run')
    parser.add_argument('--save-destination', '--vault-root', dest='save_destination', default=str(DEFAULT_VAULT), help='Folder where raw capture files should be saved. Defaults to SAVE_DESTINATION_PATH, then OBSIDIAN_VAULT_PATH, then a local runtime-artifacts folder.')
    parser.add_argument('--raw-subdir', default=str(DEFAULT_AGENT_DIR))
    parser.add_argument('--command', nargs=argparse.REMAINDER, required=True, help='Command to run after --command, e.g. --command claude -p ...')
    return parser.parse_args()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def try_parse_json(text: str) -> Any | None:
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


def try_parse_jsonl(text: str) -> list[Any] | None:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return None
    parsed = []
    for line in lines:
        try:
            parsed.append(json.loads(line))
        except Exception:
            return None
    return parsed


def main() -> int:
    args = parse_args()
    command = list(args.command)
    if command and command[0] == '--':
        command = command[1:]
    if not command:
        raise SystemExit('Pass a command after --command')

    now = datetime.now()
    year = now.strftime('%Y')
    stamp = now.strftime('%Y-%m-%d-%H%M%S')
    label = slugify(args.label)
    base_dir = Path(args.save_destination).expanduser() / Path(args.raw_subdir) / year
    ensure_dir(base_dir)

    stem = f'{stamp}-{slugify(args.project_slug)}-{label}'
    raw_path = base_dir / f'{stem}.md'
    json_path = base_dir / f'{stem}.json'
    jsonl_path = base_dir / f'{stem}.jsonl'

    completed = subprocess.run(command, capture_output=True, text=True, env=os.environ.copy())

    stdout = completed.stdout or ''
    stderr = completed.stderr or ''
    command_text = ' '.join(shlex.quote(part) for part in command)

    parsed_json = try_parse_json(stdout)
    parsed_jsonl = None if parsed_json is not None else try_parse_jsonl(stdout)

    raw_doc = f'''---
title: "{args.label}"
type: claude-raw-run
project: {args.project_slug}
agent: claude-code
runtime: claude-code
created: {now.strftime("%Y-%m-%d")}
command: {command_text}
exit_code: {completed.returncode}
stdout_json: {json_path.name if parsed_json is not None else ""}
stdout_jsonl: {jsonl_path.name if parsed_jsonl is not None else ""}
---

# {args.label}

## Command

`{command_text}`

## Exit Code

`{completed.returncode}`

## STDOUT

```text
{stdout}```

## STDERR

```text
{stderr}```
'''
    raw_path.write_text(raw_doc)

    if parsed_json is not None:
        json_path.write_text(json.dumps(parsed_json, indent=2))
    if parsed_jsonl is not None:
        jsonl_path.write_text('\\n'.join(json.dumps(item, ensure_ascii=False) for item in parsed_jsonl) + '\\n')

    if stdout:
        sys.stdout.write(stdout)
    if stderr:
        sys.stderr.write(stderr)

    print(f'\\n[claude-capture] raw={raw_path}', file=sys.stderr)
    if parsed_json is not None:
        print(f'[claude-capture] json={json_path}', file=sys.stderr)
    if parsed_jsonl is not None:
        print(f'[claude-capture] jsonl={jsonl_path}', file=sys.stderr)

    return completed.returncode


if __name__ == '__main__':
    raise SystemExit(main())

# Provenance
# - Source: internal Hermes-operator runtime-surface design.
# - Disposition: runtime-specific-adapter for Claude Code baseline.
# - Notes: baseline file copied into every Claude materialized loadout before named overlays.
