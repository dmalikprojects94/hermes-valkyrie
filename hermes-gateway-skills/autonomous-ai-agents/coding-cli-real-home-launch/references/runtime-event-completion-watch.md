# Runtime Event Completion Watch for Visible Coding Terminals

Use this pattern when Hermes launches Claude Code or Codex in a visible tmux-backed terminal but needs a cheap machine-readable completion signal.

## Principle

Do not make Hermes poll the tmux pane as the primary completion detector. The visible terminal is the user/viewer surface; runtime hooks are the authoritative completion signal.

For Claude Code, inject a per-run settings file with a `Stop` hook. For Codex CLI 0.139.0+, inject a per-run `hooks.Stop` override with `-c` and include `--dangerously-bypass-hook-trust` so the generated hook command runs without editing global Codex config. For high-trust Codex smoke runs, use `--dangerously-bypass-approvals-and-sandbox`; do not use the stale `--full-auto` flag.

Both hooks should call a repo-owned recorder such as:

```bash
python3 scripts/record_runtime_event.py \
  --manifest /path/to/manifest.json \
  --runtime codex \
  --event Stop \
  --status waiting_for_input
```

The recorder appends `events.jsonl`, stores the last event on `manifest.json`, and changes status to `waiting_for_input` or another agreed state.

## Preferred Watcher: Auto-Started and Filesystem Event Driven

Hermes should wait on filesystem events from the manifest artifact directory, not repeatedly scrape the TUI and not wake a model. On Linux, use `inotify` over the directory that contains `manifest.json` and `events.jsonl`.

The integrated coding-terminal launcher should start this watcher automatically after prompt delivery. Do not leave watcher startup as a manual operator follow-up. The normal launch sequence is: start/resume terminal, send the managed prompt, call `coding_terminal_runner.py watch-start --event-only --event-driven`, then route the eventual watcher result back to Hermes/Discord.

Default background watcher command:

```bash
python scripts/coding_terminal_runner.py watch-start \
  --manifest /path/to/manifest.json \
  --event-only \
  --event-driven \
  --timeout 21600 \
  --json
```

Check the watcher without blocking:

```bash
python scripts/coding_terminal_runner.py watch-status \
  --manifest /path/to/manifest.json \
  --json
```

Manual foreground watcher, useful for smoke tests:

```bash
python scripts/coding_terminal_runner.py watch \
  --manifest /path/to/manifest.json \
  --event-only \
  --event-driven \
  --timeout 21600 \
  --json
```

Expected successful wake shape:

```text
WATCH_RESULT terminal_state
WAKE_REASON filesystem_event
STATUS waiting_for_input
EVENT_COUNT 1
LAST_MSG <runtime sentinel or last assistant message>
```

This is near-zero CPU and zero model-token cost. It also wakes immediately when the hook writes the event file instead of waiting for the next polling interval.

## Fallback Check / Polling

For an immediate one-off check:

```bash
python scripts/coding_terminal_runner.py status \
  --manifest /path/to/manifest.json \
  --event-only \
  --json
```

If `inotify` is unavailable, fall back to low-frequency event-only polling of the manifest/event files, not tmux capture:

```bash
python scripts/coding_terminal_runner.py watch \
  --manifest /path/to/manifest.json \
  --event-only \
  --poll-interval 30 \
  --timeout 21600 \
  --json
```

## Expected Manifest Fields

The event-only status should expose enough for Hermes to route follow-up work without opening the pane:

- `status`
- `runtime`
- `tmux_session`
- `last_prompt_id`
- `last_runtime_event`
- `event_count`

For Codex Stop hooks, useful stdin payload fields include `session_id`, `turn_id`, `transcript_path`, `hook_event_name`, and `last_assistant_message`.

## Verification Recipe

1. Launch a real visible tmux-backed Claude or Codex terminal through the loadout/runner path.
2. Confirm the launcher auto-starts a background watcher and records `watcher.pid`, `watcher.log`, and `watcher-result.json` in the run artifact directory.
3. Use `watch-status --json` to verify the watcher is running before the runtime emits a Stop/completion event.
4. Prompt the runtime to return a unique sentinel string.
5. Confirm the watcher result reports `WAKE_REASON filesystem_event`, `EVENT_COUNT >= 1`, and the sentinel in `LAST_MSG` or the recorded payload.
6. Run the normal test suite afterward so the hook/watcher code, background watcher startup, and adapter command generation are covered.
7. Clean up the tmux session via the runner stop command, then verify no smoke sessions remain.

## Common Pitfalls

- Do not keep watcher startup as a separate manual step once the launcher owns the coding-terminal lifecycle. The runner should auto-start the background watcher after prompt send; manual `watch` is for diagnostics and smoke tests.
- Do not treat `blocked` or `waiting_for_input` as completion until a real runtime event exists in `events.jsonl` or `last_runtime_event`. Startup can briefly produce blocked-looking state before the agent has actually worked.
- Do not use tmux pane capture as the normal completion signal. Use it only for diagnostics or report extraction after an event is recorded.
- Do not call Codex with `--full-auto`; current Codex expects `--dangerously-bypass-approvals-and-sandbox` for that trust mode.
- Do not claim the Hermes integration is verified from raw `claude` / `codex` CLI tests alone. Exercise the actual runner or `terminal_agent`/loadout launch path when acceptance depends on Hermes orchestration.

## Operational Rule

Use tmux capture only as fallback diagnostics or for report extraction after completion. Completion awareness should come from runtime-native `Stop`/`turn.completed` events written into the manifest, and Hermes should normally wait on those file changes with an event-driven watcher.