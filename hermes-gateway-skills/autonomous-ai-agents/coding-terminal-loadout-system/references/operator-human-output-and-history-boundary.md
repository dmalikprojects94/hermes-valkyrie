# Operator Human Output and History Boundary

## Session lesson

When improving the coding-terminal loadout system's operator commands, keep a hard distinction between useful work artifacts and default historical run tracking.

Raw files and reports are still valid when they support handoff, continuity, evidence, or a concrete work product. The mistake is presenting every past coding-agent run as a default operator-history surface.

## Intended operator behavior

- Human/default command output should be readable and decision-oriented.
- JSON output should preserve full structured audit detail when `--json` is requested.
- `doctor` should answer whether the system is healthy, with concise session counts, route status, issues, and recommended actions.
- `operator-status` should emphasize current/open state: active, stopped, needs-attention, orphan sessions, and live route/watcher issues.
- `operator-status` human mode should not dump closed historical sessions. Point users to `--json`, `list`, or `reports` when they explicitly need audit/history detail.
- `reports list` should answer where closeout artifacts went, in readable per-report form, without raw Python dict/list dumps.

## Formatting pitfalls

Avoid default human output that prints Python objects directly, such as:

```text
latest_sessions: [{...}]
reports: [{...}]
```

Instead route non-JSON output through command-specific formatters. Keep the raw payload intact behind `--json`.

## Count and limit behavior

When a list command supports `--limit`, preserve the total pre-limit count separately from the shown count. Human output should say `shown of total`, not imply the limited result is the entire corpus.

## Good closeout phrasing

A good `operator-status` human message when no open sessions exist is:

```text
Open managed sessions: none
Orphan tmux sessions: none
Closed historical sessions are omitted from this human view; use --json or the list/reports commands for audit details.
```

This keeps the operator surface aligned with the operator's preference: make raw handoff/work files when needed, but do not treat every coding-agent run as a permanent historical run log/archive by default. If the operator corrects wording like “we shouldn't be keeping track of historical runs,” treat that as a workflow rule for this class of task: current-state surfaces are primary, history is explicit/on-demand, and prompt packets or handoff files should not become a default historical tracking system.
