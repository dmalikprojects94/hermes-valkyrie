# Ponytail Help

Quick reference for Ponytail behavior in Hermes-managed Claude Code and Codex terminal loadouts.

## Modes

- `ponytail lite`: build what was asked, mention the smaller alternative once.
- `ponytail full`: default; enforce YAGNI → stdlib → native → existing dependency → one-line/minimum patch.
- `ponytail ultra`: deletion-first, challenge speculative requirements while still shipping the smallest useful thing.
- `stop ponytail` / `normal mode`: stop applying Ponytail for the current session when explicitly requested.

## Available helpers

- `ponytail`: implementation simplification posture.
- `ponytail-review`: diff review for over-engineering and deletions.
- `ponytail-audit`: whole-repo complexity audit.
- `ponytail-debt`: collect `ponytail:` comments into a debt ledger.
- `ponytail-help`: this reference.

## Hermes loadout behavior

The default terminal loadout includes Ponytail posture automatically through `ponytail-default`. The helper skills are materialized into both Claude Code and Codex runtime homes so they can be invoked by name when needed.

## Provenance

- Source: https://github.com/DietrichGebert/ponytail, rev `795ec0ee3678d2fd92f7d118396855e9dcd591dc`.
- Upstream file: `skills/ponytail-help/SKILL.md`.
- Disposition: distilled-into-default.