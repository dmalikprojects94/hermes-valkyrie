# Event-driven coding-terminal watchers

Session learning: for visible Hermes-managed coding terminals, completion should be tracked from runtime-native events, not terminal text.

## Durable source of truth

Each managed coding terminal should have a manifest/artifact surface:

- `manifest.json` — current status, runtime, tmux session, prompt id, last runtime event
- `events.jsonl` — append-only lifecycle events from the runtime hook
- `last_runtime_event` — latest normalized event copied into the manifest

When Hermes sends a prompt, mark the manifest `status: working` and set `last_prompt_id`. When Codex or Claude Code finishes a turn, the runtime Stop hook should invoke a recorder that appends `events.jsonl` and updates the manifest to `status: waiting_for_input`.

## Preferred watcher

Use a non-LLM watcher. Do not spend model tokens checking whether the coding runtime is done.

Preferred Linux path:

```bash
python scripts/coding_terminal_runner.py watch \
  --manifest /path/to/manifest.json \
  --event-only \
  --event-driven \
  --json
```

This should wait on filesystem notifications from the manifest/events directory and wake when the hook writes. It avoids tmux pane capture, terminal scraping, and periodic sleep loops.

## Fallback

If filesystem notifications are unavailable, fall back to low-frequency event-only polling:

```bash
python scripts/coding_terminal_runner.py watch \
  --manifest /path/to/manifest.json \
  --event-only \
  --poll-interval 30 \
  --json
```

Polling a small manifest is acceptable as a fallback, but it should not be the preferred path when inotify/filesystem events are available.

## Dedupe rule

Supervisors should dedupe by `runtime_turn_id` or event count so the same Stop event does not trigger repeated user notifications or follow-up actions.

## Diagnostic boundary

Tmux remains the control/view layer and manual diagnostic fallback. Do not use tmux pane polling as the primary completion signal once runtime hooks are wired.
