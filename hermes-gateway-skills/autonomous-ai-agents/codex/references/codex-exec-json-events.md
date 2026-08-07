# Codex exec JSON event completion

Use this when making Codex completion-aware without relying on tmux pane polling.

Verified locally with `codex-cli 0.139.0`:

```bash
HOME=/home/<operator> codex exec \
  --json \
  --output-last-message "$RUN_DIR/last-message.txt" \
  -C "$REPO" \
  "$PROMPT" \
  > "$RUN_DIR/codex-events.jsonl"
```

A minimal successful run emitted JSONL shaped like:

```jsonl
{"type":"thread.started","thread_id":"..."}
{"type":"turn.started"}
{"type":"item.completed","item":{"id":"item_0","type":"agent_message","text":"CODEX_EVENT_SMOKE"}}
{"type":"turn.completed","usage":{"input_tokens":...,"cached_input_tokens":...,"output_tokens":...,"reasoning_output_tokens":...}}
```

`--output-last-message` wrote the final assistant text to the requested file.

Recommended manifest mapping:

- `thread.started` → record Codex `thread_id` / session id.
- `turn.started` → set status `running`.
- `item.completed` with `item.type == "agent_message"` → update last assistant message.
- `item.completed` with `command_execution`, `file_change`, `mcp_tool_call`, `collab_tool_call`, `web_search`, or `todo_list` → optional progress/artifact stream.
- `turn.completed` → append a runtime completion event and mark one-shot run `completed`.
- `turn.failed` or top-level `error` → mark run `failed`.

Do not build the first parity layer on Codex hooks. Upstream source includes lifecycle hook types such as `Stop`, `SubagentStop`, `SessionStart`, `UserPromptSubmit`, `PreToolUse`, and `PostToolUse`, and `Stop` hook stdin includes `session_id`, `turn_id`, `cwd`, `transcript_path`, `model`, `permission_mode`, `stop_hook_active`, and `last_assistant_message`. However, a local smoke using per-run `hooks.Stop` config plus `--dangerously-bypass-hook-trust` did not fire the hook under `codex exec`. Treat Codex hook support as a separate interactive/TUI investigation until a hook firing is observed in a real visible session.

For visible terminal systems, keep tmux as control/view layer. The primary one-shot completion signal should be the JSONL `turn.completed` event plus process exit, not pane text polling.