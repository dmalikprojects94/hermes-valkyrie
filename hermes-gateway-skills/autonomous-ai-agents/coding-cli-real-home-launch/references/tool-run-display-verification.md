# Tool-run display verification for integrated Claude/Codex loadout launches

Use this when Hermes has already integrated the loadout system into an agent-facing launcher such as `terminal_agent` and the remaining question is whether the operator-facing UI tells the truth.

## What to verify

Check both phases of the visible tool run:

1. **Pre-launch preview / spinner text**
   - Should use a human-friendly runtime label, not the raw internal key.
   - Examples: `Claude Code`, `Codex`
   - If a loadout is known from arguments, include it there too.

2. **Post-run completion / cute line / final summary**
   - Should prefer the resolved runtime/loadout metadata returned by the tool result.
   - This matters when the request was `auto` or when resolution happened inside the launcher.

## Expected display shape

Good examples:

- `Claude Code · loadout deep-coding`
- `Codex · loadout coding`

Avoid:

- raw runtime keys only: `claude`, `codex`
- generic tool labels that hide the runtime
- completion lines that echo the request when the launcher actually applied a different loadout

## Minimum validation pattern

1. Run targeted display tests covering:
   - runtime label mapping (`claude` -> `Claude Code`)
   - explicit loadout display from args for previews
   - resolved loadout display from result payloads for final summaries
2. Run the launcher's own tests so the metadata field carrying the applied loadout is still emitted.
3. Execute one real smoke run through the integrated launcher and assert:
   - the preview text contains runtime + loadout
   - the result payload includes the applied loadout
   - the rendered final tool line uses the resolved runtime + loadout string

## Session pattern that worked here

A strong smoke run used a one-line sentinel response from Claude Code so UI verification stayed easy to inspect. The value of the prompt was not the content quality; it was proving that the integrated launcher, metadata plumbing, and user-visible tool-run messaging all agreed on the same runtime/loadout state.

## Why this matters

Dry-run success is not enough once the launch path is user-facing. If the tool-run text does not identify the runtime and resolved loadout, operator trust drops and troubleshooting gets slower. The integrated flow should say which coding agent Hermes actually used and which loadout it actually applied.
