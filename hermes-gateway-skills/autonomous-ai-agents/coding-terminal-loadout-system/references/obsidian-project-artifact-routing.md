# Save-Destination Project Artifact Routing

Use this reference when coding-terminal reports appear in repo-local Hermes artifact folders or generic raw lanes instead of the configured save-destination project tree. The save destination is set with `SAVE_DESTINATION_PATH`; `OBSIDIAN_VAULT_PATH` remains supported as a legacy alias.

## Intended routing contract

- Raw runtime transcripts/reports route by agent runtime:
  - Claude Code: `$SAVE_DESTINATION_PATH/agents/claude-code/raw-runs/`
  - Codex: `$SAVE_DESTINATION_PATH/agents/codex/raw-runs/`
  - Unknown/other: `$SAVE_DESTINATION_PATH/agents/coding-terminal/raw-runs/`
- Structured project reports route by project slug:
  - `$SAVE_DESTINATION_PATH/projects/<project-slug>/artifacts/coding-terminal-runs/`
- Repo-local `local-runtime-artifacts/projects/<project>/coding-terminal-runs/` is fallback only, not the healthy default when the configured save destination is available.

## Bug pattern

A run can look successful while still writing the structured report into a local Hermes/project artifact directory. This usually means the artifact router or an existing manifest preserved an old `project_output_root`/route decision even though the save-destination path is valid.

Symptoms:

- `latest_report` exists locally but no project mirror appears in the save destination.
- `reports list` shows missing raw/project copies.
- `operator-status` reports a fallback `raw_root_source` or `project_root_source` when save-destination capture was expected.
- Old managed manifests keep stale route paths after the router default changed.

## Fix workflow

1. Confirm the save-destination path is set and writable: `SAVE_DESTINATION_PATH=/path/to/save-destination` (or the legacy `OBSIDIAN_VAULT_PATH` alias).
2. Check route preflight with `doctor` and `operator-status --json`; inspect `raw_root_source`, `project_root_source`, and route warnings.
3. If defaults are wrong, patch `scripts/artifact_router.py` so raw roots use the runtime agent lane and project roots prefer `projects/<slug>/artifacts/coding-terminal-runs/` under the save destination.
4. Patch operator surfaces to validate both raw and project roots; a raw-only preflight is not enough.
5. Update tests so the save-destination project route is a contract, not just a behavior observed in one run.
6. Run `reports repair` to backfill surviving historical reports into raw/project save-destination lanes. This copies/redacts existing reports; it should not synthesize a new model-authored report.
7. Operators may layer their own note-system indexing or sync (for example a personal knowledge base or backup pipeline) on top of the save destination; that is outside this routing contract.

## Verification commands

From the repo root:

```bash
python scripts/coding_terminal_runner.py doctor --repo <repo-path> --json
python scripts/coding_terminal_runner.py operator-status --repo <repo-path> --json
python scripts/coding_terminal_runner.py reports list --repo <repo-path> --json
python scripts/coding_terminal_runner.py reports repair --repo <repo-path> --json
python scripts/validate_loadouts.py
python scripts/smoke_clean_hermes_onboarding.py --json
```

Expected evidence:

- `raw_root_source` and `project_root_source` point at the save destination when it is available.
- `reports list` shows local report, raw save-destination copy, and project mirror copy where applicable.
- Tests cover both runtime raw lanes and project artifact mirroring.

## Pitfalls

- Do not treat raw runtime storage and structured project mirroring as the same thing. Both must be checked.
- Do not stop at changing defaults if existing manifests still point to stale roots; repair/backfill them or explicitly report what remains old.
- Do not commit raw runtime transcripts. Track project artifact summaries/reports only when they are intended durable project docs.
- Do not claim save-destination routing is fixed from a dry-run alone; verify with `reports list`/`repair` and a route preflight.
