# Hermes Valkyrie

Portable loadout and lifecycle management for Hermes-launched Claude Code and Codex terminal runs.

## What it does

Hermes Valkyrie provides a deterministic way to prepare and run terminal coding agents. It separates two decisions before launch:

| Decision | Meaning |
| --- | --- |
| Runtime | Which terminal coding agent executes the task, currently Claude Code or Codex. |
| Loadout | Which behavior surface the runtime receives: `default` plus the specialty loadouts listed in the README loadout itinerary. |

The repo materializes the selected loadout into runtime-specific files, validates the result, launches through a managed runner when requested, watches for completion, and extracts a structured closeout report.

## Public quickstart

```bash
python scripts/validate_loadouts.py
python scripts/resolve_route.py --runtime claude --request "Use Claude for research" --explicit-loadout research
python scripts/apply_loadout.py --runtime claude --loadout research --output-root output
python scripts/apply_loadout.py --runtime codex --loadout research --output-root output
```

The generated runtime surfaces land under `output/`. That folder is ignored and should not be committed.

## Documentation

Start with:

- [Documentation index](README.md)
- [Install guide](INSTALL.md)
- [Architecture overview](architecture/README.md)
- [Routing model](architecture/routing-model.md)
- [Runtime adapters](architecture/runtime-adapters.md)
- [Managed visible launch contract](guides/managed-visible-launch-contract.md)
- [Troubleshooting](guides/troubleshooting.md)

## Repository shape

```text
.github/workflows/     Public-safe validation workflow for clean checkouts.
adapters/              Runtime-specific materialization maps and commands.
config/                Safe example configuration.
docs/                  Public documentation.
examples/              Minimal example routing/loadout files.
hermes-gateway-skills/ Optional Hermes bridge skill snapshots.
loadouts/              Named loadout definitions and overlays.
scripts/               Validation, route resolution, materialization, and managed-runner tools.
shared/                Reusable shared instructions, skills, hooks, and packs.
spec/                  Loadout schema.
```

## Safety boundary

Do not commit local runtime homes, `.env` secrets, `.hermes/`, `.claude/`, `.codex/`, prompts, generated output, vault paths, Discord IDs, or operator-specific state. Use sandbox output first and live-home writes only after explicit operator approval.

## Release boundary

Maintainer note (upstream development only): public releases of this system are produced by extraction from the maintainer development workspace and reviewed as a local artifact before publication. If you received this repo as the public tree, it already is the release; nothing in this section applies to you.
