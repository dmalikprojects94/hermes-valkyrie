# Hermes Claude Default Surface

This is the concrete default Claude Code surface for the Hermes Terminal Loadout system.

## Operating contract

- Treat this file plus the markdown files under `rules/` as the active operating surface.
- Treat `commands/` and `agents/` as concrete reusable runtime assets, not placeholders.
- Do not invent your own reporting format. Use the reporting contract in `rules/10-reporting-format.md`.
- When the task prompt is broad, ambiguous, or likely to sprawl, run the prompt-prep workflow in `rules/20-prompt-prep-pipeline.md` before implementation.
- When a Hermes-managed Claude run needs durable capture, use `bin/claude_capture_wrapper.py` so raw output and structured output land under `$SAVE_DESTINATION_PATH/agents/<agent>/raw-runs/`.

## Runtime boundaries

- This default surface is the stable Claude baseline.
- Hermes may copy additional command files, agent files, skills, rules, hooks, or MCP configs into this runtime home when a concrete specialty loadout exists.
- If no specialty Claude overlay exists yet, keep working from this default baseline rather than synthesizing a new surface.

## Prompt prep before coding

Use the prompt-prep pipeline when:
- the request is vague
- the deliverable shape is unclear
- verification is missing
- the task could easily balloon into adjacent work

The required prompt-prep output lives in `rules/20-prompt-prep-pipeline.md` and the reusable template lives in `templates/prompt-prep-template.md`.

## Final reporting

Normal substantial runs must end with the exact report headings defined in `rules/10-reporting-format.md`.

## Capture policy

For Hermes-launched Claude runs that need durable evidence:
- write the raw transcript to the save destination lane `$SAVE_DESTINATION_PATH/agents/<agent>/raw-runs/` (fall back to `./local-runtime-artifacts/raw-capture/agents/<agent>/raw-runs/` when no save destination is set)
- write structured JSON or stream-JSON sidecars when available
- promote human-usable summaries into the appropriate daily or project notes separately

Raw capture is provenance only; coding-terminal closeout artifacts are the source of truth. Use the runtime-specific agent lane, e.g. `agents/claude-code/raw-runs/YYYY/`.

## Session posture

- Prefer fresh Claude sessions for major workstream changes.
- Treat roughly 35-55% context usage as the warning band.
- Compact or relaunch before the session becomes bloated.

## Provenance

- Source: internal Hermes-operator runtime-surface design.
- Disposition: runtime-specific-adapter for Claude Code baseline.
- Notes: baseline file copied into every Claude materialized loadout before named overlays.
