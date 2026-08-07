# Live Managed Audit Closeout Proof

Use this reference when the operator asks whether Claude Code/Codex sessions actually close, where reports land, or whether watcher/closeout/reporting is solid enough for live use.

## What the live audit proved

A paired live run used the managed loadout runner for both runtimes with visible tmux terminals, watcher enabled, structured closeout, report routing, and auto-stop after closeout.

Successful evidence to look for in future runs:

- `operator-status` before launch shows no active, needs-attention, runtime-event-failed, or orphan sessions.
- The manifest records desktop-window proof when visibility was requested; tmux attachment alone is not sufficient.
- The watcher wakes from a runtime/terminal event rather than a blind polling loop.
- Closeout returns `status: structured` and has no blockers.
- The manifest records `event_count >= 1`, a Stop/final event, `latest_report`, and `stop_after_closeout_applied: true` for one-shot watched runs.
- `operator-status` after the run shows `active: 0`, `open_managed: 0`, `orphan_tmux: 0`, and `runtime_event_recording_failed: 0`.
- `doctor` reports `ok` and says report routing is ready.

## Closeout versus closing

Closeout extracts and routes the final report. Closing the terminal is a separate lifecycle action. The safe policy is:

- auto-stop a watched one-shot run only after structured closeout with no blockers;
- keep sessions open when they are active, blocked, failed, malformed, or missing a final message;
- use `--keep-open-after-closeout` when the operator wants to inspect or resume the terminal;
- use `orphans list` / `orphans cleanup` for unmanaged tmux sessions rather than killing panes manually.

If the operator says sessions are still open, do not guess. Run `doctor`, `operator-status`, and `orphans list`; report the exact lifecycle state and why the session was or was not closed.

## Report routing locations

For successful runtime-specific routes, reports should exist in three places:

- local manifest report under `local-runtime-artifacts/coding-terminals/<label>/reports/`;
- raw save-destination lane under `$SAVE_DESTINATION_PATH/agents/<runtime>/raw-runs/`;
- project mirror under `$SAVE_DESTINATION_PATH/projects/<project-slug>/artifacts/coding-terminal-runs/`.

Runtime lanes:

- Claude Code: `agents/claude-code/raw-runs/`
- Codex: `agents/codex/raw-runs/`
- unknown/fallback: `agents/coding-terminal/raw-runs/`

`reports list` is the first tool for “where did the files go?” and `reports repair` is the safe backfill path when a routed copy is missing but another report copy survives.

## Known diagnostic polish from the live audit

The core lifecycle path worked, but two diagnostic edges are worth checking before claiming the system is perfect:

1. `operator-status`/`doctor` route preflight can show the generic raw lane (`agents/coding-terminal/raw-runs`) even when the actual runtime-specific lanes work. Treat this as a diagnostic mismatch unless `reports list` shows missing runtime-specific copies.
2. Older snapshot-only sessions may have `latest_report` populated while `closeout_status` is `not_run`; `reports list` can under-count these as closeout-routed reports. Prefer `reports repair --dry-run` or direct manifest/report inspection when auditing old sessions.

Do not encode a transient failure as a durable rule. Capture the durable pattern: preflight, visible proof, structured closeout, routed copies, auto-stop, final `doctor ok`.

## Recommended live-smoke checklist

```bash
cd /home/<operator>/projects/<GITHUB_REPO_NAME>
python scripts/coding_terminal_runner.py doctor --repo . --json
python scripts/coding_terminal_runner.py operator-status --repo . --json
python scripts/list_runtime_commands.py --runtime claude --loadout default --compare codex
python scripts/run_loaded_agent.py --runtime <claude|codex> --loadout default --repo . --task-file <prompt.md> --label <label> --bypass-permissions --watch --watch-seconds 1200 --json
python scripts/coding_terminal_runner.py reports list --repo . --json
python scripts/coding_terminal_runner.py doctor --repo . --json
python scripts/validate_loadouts.py
python scripts/smoke_clean_hermes_onboarding.py --json
```

For Codex live audits, prefer startup prompt transport (`input_transport: initial_prompt`) for fresh sessions so the managed prompt is injected reliably and tracked as the active turn.
