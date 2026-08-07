# Goal closeout and operator hardening notes

Use these notes when a future Claude/Codex run uses `/goal` to harden the terminal-loadout system itself, or when closeout/report routing looks ambiguous.

## Durable lessons from the hardening pass

- Treat `operator-status --json` as the top-level truth surface before and after launches. It should combine managed manifests, real tmux state, orphan Claude/Codex tmux sessions, lifecycle counts, closeout status, and report-route preflight.
- Closed sessions should not show stale in-flight statuses by default. Preserve the original manifest value separately as `manifest_status`, but display `closed` when tmux is gone.
- Null closeout/status values should be normalized for operators (`not_run` or `unknown`) instead of being surfaced as raw nulls.
- Startup cleanup should only stop sessions that are both live in tmux and `auto_cleanup_safe == true`; blocked/failed/active sessions stay open for inspection.
- Claude `/goal` closeout reports may use task-specific headings such as `Non-ambiguous Work Completed` and `Qualifying Questions`. The closeout parser should accept `Non-ambiguous Work Completed` as an alias for `Changes` and preserve `Qualifying Questions` when present, otherwise structured reports can be misrouted as raw-only.
- A malformed closeout summary must not abort raw report archival; route it as unstructured so Obsidian still gets the evidence.
- Runtime event write failures should be visible on stderr as well as fallback artifacts; silent event loss makes watcher/closeout debugging too hard.
- Codex completion reports should take priority over update-banner or press-enter noise, otherwise completed Codex runs can be misclassified as blocked.

## Verification pattern

After a terminal-loadout hardening change, run:

```bash
python scripts/validate_loadouts.py
python scripts/smoke_clean_hermes_onboarding.py --json
python scripts/coding_terminal_runner.py operator-status --repo /home/<operator>/projects/<GITHUB_REPO_NAME> --json
```

For a live `/goal` run, verify that structured closeout produced both:

```text
$SAVE_DESTINATION_PATH/agents/<runtime>/raw-runs/<stamp>-<runtime>-<label>-report.md
/home/<operator>/projects/<GITHUB_REPO_NAME>/local-runtime-artifacts/projects/<GITHUB_REPO_NAME>/coding-terminal-runs/<stamp>-<runtime>-<label>-report.md
```

Then run `cleanup-stopped --json` and confirm `operator-status` shows `open_managed: 0`, `orphan_tmux: 0`, and no route warnings unless the operator intentionally wants the terminal left open.

## Qualifying-question boundary

Do not guess policy choices. Ask the operator when deciding:

- whether redaction should scan final model-authored report/summary text in addition to runtime provenance;
- how broad the no-blockers vocabulary should be for auto-stop;
- what lifecycle state a `no_final_message` closeout should imply;
- how strict watcher PID-reuse/crashed-watcher detection should be;
- whether generic words like `error` or `failed` should remain blocked markers despite false positives;
- whether the single-machine `HOME=/home/<operator>` runtime assumption should stay hardcoded or become configurable.
