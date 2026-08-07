# Hermes Update Readiness

Run the Hermes terminal-loadout update readiness loop.

Use this when a Hermes Agent update might affect the terminal loadout system, Claude Code/Codex access, loadout materialization, watcher/closeout behavior, or save-destination report routing.

## Procedure

1. Load and follow the shared `hermes-update-readiness` skill.
2. Treat the current terminal-loadout repo and the selected Hermes profile/sandbox as the source inputs.
3. Do not run production `hermes update`, restart gateway, overwrite live config, or print secrets.
4. Run the checks with real command output.
5. End with the required decision: `READY`, `REPAIR_REQUIRED`, `BLOCKED`, or `DO_NOT_UPDATE`.

## Output

Return the structured readiness report from the shared skill, including baseline, diff classification, overlay reconciliation, verification output, required fixes, and cutover blockers.

## Provenance

- Source: terminal-loadout shared update-readiness skill.
- Disposition: runtime-specific-adapter for Claude Code default.
- Notes: exposes shared behavior as a Claude slash-command workflow surface.
