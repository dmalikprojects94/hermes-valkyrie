# Claude Capture Policy

Use the capture wrapper for Hermes-managed Claude runs when durable evidence matters.

## Required outputs

- A raw transcript artifact in the save destination lane: `$SAVE_DESTINATION_PATH/agents/<agent>/raw-runs/` (falling back to `./local-runtime-artifacts/raw-capture/agents/<agent>/raw-runs/` when no save destination is configured)
- A structured sidecar when Claude is run with `--output-format json` or `--output-format stream-json`
- A normal Hermes-facing final report using the standard report headings

Capture is provenance, not canonical memory. The coding-terminal closeout artifacts are the source of truth for a run; this wrapper only preserves raw evidence. Use the runtime-specific agent lane, e.g. `agents/claude-code/raw-runs/YYYY/`.

## Preferred modes

- Use `claude -p --output-format json` for one-shot structured runs.
- Use `claude -p --output-format stream-json --include-partial-messages --include-hook-events` when event-level capture matters.
- Reserve visible interactive TUI sessions for behavior verification or multi-turn work where a live terminal matters.

## Provenance

- Source: internal Hermes-operator runtime-surface design.
- Disposition: runtime-specific-adapter for Claude Code baseline.
- Notes: baseline file copied into every Claude materialized loadout before named overlays.
