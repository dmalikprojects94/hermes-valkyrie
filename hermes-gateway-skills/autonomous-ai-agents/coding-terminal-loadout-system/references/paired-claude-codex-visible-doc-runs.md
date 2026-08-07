# Paired Claude/Codex visible documentation runs

Use this reference when the operator asks to launch both Claude Code and Codex publicly/visibly to document or audit the loadout system itself.

## Pattern that worked

1. Preflight with `operator-status --json` before launching. Confirm no open managed sessions, no orphan tmux sessions, and raw report routing points at the configured save destination (`$SAVE_DESTINATION_PATH/agents/<runtime>/raw-runs/`) with a save-destination raw root source.
2. Generate separate enhanced prompt files under the repo ignored prompt area, one per runtime. Include runtime/loadout identity, exact target doc path, source surfaces to inspect, verification commands, final report headings, and `Do not commit or push` unless the operator asked for that.
3. Launch both through `scripts/run_loaded_agent.py`, not raw `claude`/`codex`, with visible terminals enabled. For one-shot doc/audit tasks, `--watch --closeout --keep-open-after-closeout --watch-seconds <large>` is appropriate for the operator-visible verification: sessions remain visible after successful structured closeout until the operator intentionally stops them. Use `--stop-after-closeout` only for explicit one-shot cleanup.
4. Verify visibility shortly after launch with `operator-status --json`, `tmux list-clients`, and desktop-window proof from the manifest (`visible_terminal_proof.status == desktop_window` with window IDs) or an equivalent Computer Use/window backend. Do not tell the operator the sessions are visible until desktop-window proof exists; attached tmux clients alone are not enough.
5. Wait for the runner processes to exit. Confirm closeout reports were routed to both the project mirror and the main save-destination raw archive.
6. Run `python scripts/validate_loadouts.py` and `python scripts/smoke_clean_hermes_onboarding.py --json` after the agents finish.
7. Inspect `git status` and `git diff` before reporting. Coding agents can make broad incidental changes while inspecting/mutating loadout surfaces. Restore unrelated edits and rerun validation/tests so the final working tree contains only the requested deliverables.

## Report path distinction

Operator output may show `latest_report` as a local project mirror under `local-runtime-artifacts/projects/<project>/coding-terminal-runs`. That does not mean save-destination routing failed. Check manifest artifact fields for `latest_raw_report` and confirm it resolves under the configured save destination.

## Pitfall

Do not leave broad source/provenance edits from the agents in the working tree unless the operator explicitly asked for those changes. A successful paired run can still produce extra edits; cleanup and verification are part of the task, not optional polish.
