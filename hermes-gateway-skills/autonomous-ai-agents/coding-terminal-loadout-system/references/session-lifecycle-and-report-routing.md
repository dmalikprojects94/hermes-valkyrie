# Session lifecycle and report routing lessons

Use this note when a coding-terminal run leaves Claude Code or Codex panes open, when the operator asks why sessions were not closed, or when verifying reporter/watch behavior.

## Core distinction

`closeout` means: extract the runtime's final answer, redact it, route report artifacts, and mark the manifest. It does **not** necessarily close the tmux/Codex/Claude session.

Actual terminal closure happens only through one of these paths:

- launch with `--keep-open-after-closeout` for the operator-visible verification so the terminal remains inspectable after closeout; use `--stop-after-closeout` only for explicit one-shot cleanup, which closes only after a structured closeout with no blockers;
- explicit `coding_terminal_runner.py stop --manifest <manifest.json> --json`;
- explicit safe cleanup of stopped sessions via `cleanup-stopped`.

Blocked, failed, `needs_attention`, unstructured, or `no_final_message` sessions are intentionally left open for inspection unless the operator explicitly tells you to close them.

## Operational pre/postflight

Before a new delegated Claude/Codex run, check the combined operator surface with `operator-status --json`. If there are stale/stopped sessions, close them safely before launching unless preserving them is part of the task.

For the operator-visible documentation/review/development verification, default to `--stop-after-closeout` so successful structured closeouts do not leave stale terminals open. Use `--keep-open-after-closeout` only when the operator explicitly wants inspection, live terminal behavior verification, or follow-up in the same terminal. The stop flag remains conservative: structured closeout with no blockers closes; missing final messages, malformed watcher output, partial watcher results, failed/blocked/unstructured reports, and no-final-message cases remain open.

After the run, verify session state again with `operator-status --json`. Do not tell the operator the workflow is clean if sessions remain open without naming why they remain open.

## Reporter/routing verification

A successful report path should be backed by manifest data, not assumption. Inspect these fields before reporting completion:

- `closeout.status`
- `latest_report`
- artifact route/preflight fields, especially the raw root source
- watcher result, especially `watcher_wait.result.watch_result`

Reports should route into the configured save destination under `agents/<agent>/raw-runs/` when the save-destination environment/path is present and writable. If reports fall back to an artifact root, state that as a blocker or repair item when the operator asked for save-destination capture.

## User-facing closeout language

When the operator asks what happened, answer directly in operational terms: which sessions are still open, why they were left open, whether closeout ran, where the report landed, and what fix was made. Avoid implying that report extraction equals terminal cleanup.