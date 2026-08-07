# Claude `/goal` raw-command lifecycle

Use this when the operator explicitly wants real Claude Code `/goal` behavior inside the managed coding-terminal system.

## Why

`run_loaded_agent.py` is correct for ordinary Claude delegation, but for Claude it sends the task through Hermes prompt management. If the task text begins with `/goal`, the wrapper can embed that line inside prose, so the live Claude TUI may not receive `/goal` as an actual slash command. For true slash-command proof, keep the managed lifecycle but send the `/goal` command raw.

## Pattern

For a whole multi-phase implementation, first create or point Claude at a canonical roadmap/design doc, then create a repo-owned prompt packet that references it. The prompt packet is the live `/goal` handoff, not a historical run log.

1. Create a repo-owned prompt packet, usually `agent-prompts/<topic>.md` or another ignored local task-file path.
2. Put the full command on line 1:

```text
/goal <complete standing completion condition>
```

3. Put the detailed implementation/design spec below it.
4. Start a fresh visible Claude terminal with the low-level runner:

```bash
python scripts/coding_terminal_runner.py start \
  --runtime claude \
  --loadout default \
  --repo /path/to/target/repo \
  --label <label> \
  --project-slug <project-slug> \
  --bypass-permissions \
  --visible \
  --json
```

5. Submit the first line as a raw prompt:

```bash
python scripts/coding_terminal_runner.py send \
  --manifest /path/to/manifest.json \
  --prompt "$(sed -n '1p' /path/to/repo/agent-prompts/<topic>.md)" \
  --raw-prompt \
  --json
```

6. Submit a short raw follow-up:

```text
Read and execute @agent-prompts/<topic>.md now. Treat the first-line /goal as already active; use the rest of the file as the implementation spec.
```

7. Start/watch closeout through the normal event-driven path:

```bash
python scripts/coding_terminal_runner.py watch-start --manifest /path/to/manifest.json --timeout 2400 --event-only --event-driven --json
python scripts/coding_terminal_runner.py closeout --manifest /path/to/manifest.json --wait --timeout 560 --json
```

8. Verify the artifact independently, then stop the session when structured closeout has no blockers:

```bash
python scripts/coding_terminal_runner.py stop --manifest /path/to/manifest.json --json
```

## Reporting checklist

Report the desktop-window proof, tmux client state, target repo, changed files, verification output, routed report paths when useful, and final stopped/closed session state. Do not commit unless the operator explicitly asks.