# Command Inventory

List the slash-command and command-equivalent surface currently bound into this Hermes loadout.

## Procedure

1. Read `hermes-loadout.json` in the runtime home to confirm the active runtime/loadout.
2. Read `command-inventory.json` for the machine-readable command list.
3. Read `command-inventory.md` for the operator-facing summary.
4. Report commands by invocation, kind, source, and purpose. If a command the operator expects is missing, say it is not bound to this loadout instead of guessing.

## Notes

- Claude Code slash commands are materialized as Markdown files under `commands/`.
- Codex native slash commands are tracked from `adapters/codex/commands.yaml`; Hermes-managed command equivalents are skills exposed in the Codex skill list.
- The loadout system regenerates this inventory during `apply_loadout`, so stale inventories indicate the loadout was not re-applied.

## Provenance

- Source: local Claude-OC-System default command inventory plus internal Hermes-operator adaptation.
- Disposition: runtime-specific-adapter for Claude Code default.
- Notes: exposes shared default behavior as Claude slash-command workflow surface.
