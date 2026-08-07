# Event-Driven Closeout Review Checklist

Use this when reviewing a Claude Code run that implemented Hermes terminal-run closeout, watcher, artifact-routing, or loadout orchestration changes.

## What this session taught

A full suite pass is not enough for watcher/closeout work. Event-driven watcher code can be race-prone while still passing once. In one review, a targeted watcher test passed twice and failed on the third repeat because the watcher returned `wake_reason: initial` instead of `filesystem_event` when the terminal state was already visible before the inotify wait began.

## Review steps

1. Compare implementation against the written build spec or acceptance criteria, not just Claude's final report.
2. Run the project-wide checks, then repeat targeted watcher/event tests several times to expose timing races.
3. Inspect whether normal completion uses runtime event files and closeout JSON rather than tmux pane/status scraping.
4. Verify persisted artifacts, not only returned command JSON. For report extraction, check the on-disk summary JSON includes every promised field.
5. Check fallback ordering explicitly: watcher-result payload, watcher-result top-level event, manifest event, events.jsonl, and snapshot fallback only when explicitly enabled.
6. For launcher integration, add or run a regression proving blocking `--watch` calls `closeout --wait` instead of `status --refresh` pane capture.
7. Redaction review must include every artifact path that can persist model output: reports, summaries, provenance files, raw Obsidian copies, project archive copies, and any snapshot fallback path.
8. If a visible-runtime smoke test was skipped, report that as incomplete verification even when synthetic closeout and unit tests pass.

## Red flags

- A test asserts exact `wake_reason: filesystem_event` without accounting for a valid pre-existing terminal state race.
- Dry-run wording tests are the only proof for a runtime behavior change.
- The returned Python dict has fields missing from the JSON written to disk.
- Closeout waits for a watcher timeout even though manifest/events already contain the final message.
- Snapshot-based reports bypass redaction while event-based closeout is redacted.
