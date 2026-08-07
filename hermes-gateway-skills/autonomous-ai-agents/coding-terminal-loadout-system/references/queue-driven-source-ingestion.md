# Queue-driven source ingestion for loadout amalgamation

Use this reference when the operator wants to continue building the coding-terminal loadout system from GitHub star lists or promising Claude/Codex repos without waiting for another approval at each repo.

## Pattern learned

When the operator says to continue the project until it is done, treat the saved source queue as the worklist. For each repo, run a source-accounted **classification pass before migration**. Do not copy upstream runtime material into `default`, `loadouts/`, `shared/`, `adapters/`, hooks, commands, or agents until a report has identified the exact portable value and a recommendation ledger has mapped each useful source surface to a target loadout/shared surface.

The safe iteration unit is:

1. View the saved queue in the maintainer source registry (not shipped publicly) and find the next unreported repo.
2. Capture the repo's metadata and the recommended report path from the same registry tooling.
3. Launch a visible Claude Code run through `scripts/coding_terminal_runner.py` with the `default` loadout and an enhanced prompt file.
4. In the prompt, explicitly require: no migration, preserve uncommitted work, create one ingestion report, produce a recommendation ledger grouped by target loadout, update the source matrix, queue doc, and the maintainer source registry, run verification, and do not commit.
5. Watch event-driven closeout, then verify locally rather than trusting the child summary.
6. Stop the completed managed session and run `cleanup-stopped`; report any unrelated orphan tmux sessions separately.

## Verification after every report pass

Run these from `/home/<operator>/projects/<GITHUB_REPO_NAME>`:

```bash
python scripts/validate_loadouts.py
python scripts/smoke_clean_hermes_onboarding.py --json
git diff --check
```

Also check that the new report exists, has no accidental XML/tool wrapper tags such as `</content>` or `</invoke>`, and that `the private source-list registry` parses.

## Report shape

Each report should use the maintainer ingestion-report template (not shipped publicly) and include:

- upstream URL, clone path, exact revision, license, source type, mode, status;
- inventory of meaningful surface groups, not necessarily every file when the repo has thousands of generated/localized files;
- per-group disposition using the maintainer source-provenance contract vocabulary;
- Claude/Codex parity mapping using `docs/loadout-synchronization-contract.md`;
- clear `rejected`, `superseded`, `deferred`, and `repo-resident` sections;
- a direct statement that net materialized runtime files were `0` when the pass is classification-only;
- next build targets by loadout/adapter (`default`, `coding`, `deep-coding`, `project-planner`, `research`, `security`, Codex adapter, Claude hooks, etc.);
- a recommendation ledger that lists source path, decision, target loadout, target surface, overlap/supersession, and provenance for every useful skill/source surface.

## Classification heuristics from the first queue passes

- `default` is almost closed. Only admit tiny, broad, low-ceremony distilled doctrine after an explicit admission test.
- If a repo has real skills, inspect skill files directly and make source-path-level recommendations. Do not summarize the whole repo as one vague candidate.
- Useful non-default skill material should usually land in `coding`, `deep-coding`, `project-planner`, or `loadout-management`/adapters; if none fits, say why and only then propose a new loadout task pack.
- Heavy daemon-backed products should usually be rejected as engines, while preserving narrow architectural lessons.
- Multi-runtime repos are valuable as parity exemplars even when their skill text is superseded.
- Prefer adopting patterns, not files: adapter registries, SessionStart skill bootstrap, tool-name maps, graceful hook degradation, capability baselines, prompt-defense rules, and research-first/security playbooks.
- Treat generated per-runtime directories, localized doc bulk, product packaging, telemetry/data stores, installer scripts, and branded distribution manifests as rejected unless a later micro-pass proves a portable need.

## Prompt snippet

```text
Create a full source-accounted ingestion report for <owner/repo> using the maintainer ingestion-report template, source-provenance contract, and loadout-synchronization contract.
Do not migrate runtime material in this pass. Preserve existing uncommitted work. Inspect skill-bearing paths directly, produce a recommendation ledger grouped by target loadout, and make sure every useful source surface is marked recommend-add, recommend-patch-existing, already-covered, adapter-only, deferred, or rejected. Update the source matrix, the queue doc, and the maintainer source registry. Run python scripts/validate_loadouts.py, python scripts/smoke_clean_hermes_onboarding.py --json, and git diff --check. Do not commit.
```
