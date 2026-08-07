# Source-List Onboarding Command System

Use this reference when the operator wants to turn a GitHub repo, star list, prompt pack, Claude Code pack, Codex pack, hook pack, MCP pack, or other upstream agent stack into source-accounted loadout material.

## Core lesson

Do not keep onboarding as a one-off Claude prompt or a flat report-writing habit. Treat source onboarding as a first-class command surface in the loadout repo, backed by structured registry/state data and rendered Markdown artifacts.

The preferred implementation path is to extend the existing maintainer source-registry tooling (not shipped publicly) rather than creating a detached script. The tool should understand saved source-list aliases from the maintainer source registry, maintain queue states, generate audit/synthesis outputs, produce recommendation ledgers, and then produce/apply migration task packs without blindly changing runtime loadouts.

## Durable command shape

A good source-list onboarding surface (implemented in the maintainer source-registry tooling, not shipped publicly) exposes subcommands along these lines:

```text
status <list-alias>
audit <repo-or-alias>
synthesize <repo-or-alias>
recommend-repo <owner/repo|url>
hypotheses <list-alias>
migrate-plan <repo-or-alias>
apply-recommendations <owner/repo|url> --dry-run
onboard <repo-or-alias>
```

Names may evolve, but preserve the separation of responsibilities:

- `status`: summarize queue coverage, states, gaps, next repo, and known artifacts.
- `audit`: inventory upstream material and classify it without migration.
- `synthesize`: extract reusable patterns into adopted/rejected/deferred provenance.
- `recommend-repo`: inspect repo-pinned skill/source surfaces and emit concrete add/patch/defer/reject recommendations grouped by target loadout.
- `hypotheses`: propose candidate loadouts or improvements from multiple audited sources.
- `migrate-plan`: create an explicit, reviewable task pack for source-derived changes.
- `apply-recommendations`: default to dry-run; when explicitly applying, patch shared surfaces and existing loadout YAML, then verify materialization.
- `onboard`: orchestrate the above stages, ideally with `--dry-run`, `--limit`, `--apply` as an explicit opt-in, and no-commit defaults.

## State model

Use JSON as canonical state and render Markdown from it. Avoid hand-maintained-only status tables.

Useful queue states:

- `unvisited`
- `audited`
- `synthesized`
- `recommended`
- `hypothesis`
- `migration_planned`
- `applied`
- `materialized`
- `rejected`
- `deferred`

Each repo should carry source metadata, local clone/cache path if any, latest artifact paths, adopted/rejected/deferred counts, candidate loadouts, Claude/Codex parity status, and next recommended action.

## Artifact layout

Prefer predictable paths:

```text
the maintainer source registry (not shipped publicly)
<sources-lane>/<SOURCE>-INGESTION-YYYY-MM-DD.md
<sources-lane>/<SOURCE>-SYNTHESIS-YYYY-MM-DD.md
<recommendations-lane>/<SOURCE>-RECOMMENDATIONS-YYYY-MM-DD.md
<sources-lane>/SOURCE-MATRIX.md
<sources-lane>/<queue-doc>.md
<hypotheses-lane>/<loadout-name>.md
<onboarding-results-lane>/<SOURCE>-RESULT-YYYY-MM-DD.md
<plans-lane>/<topic>-YYYY-MM-DD.md
```

When a Claude `/plan` prompt is used to bootstrap the system design, keep it as a durable prompt artifact under an ignored local task-file directory such as `agent-prompts/`, but convert the result into an explicit public build spec so the repo does not depend on transient terminal history.

## Source-accounting rules

Every meaningful upstream item must land in one of:

- `adopted`: source-derived material that should become shared/loadout/runtime behavior.
- `deferred`: promising but not ready; record the condition that would unblock it.
- `rejected`: intentionally not adopted; record why.

For classification-only passes, explicitly record net runtime materialization as `0`. Do not migrate files during audit unless the user explicitly asked for implementation.

## Recommendation ledger rules

For skill-bearing repos, `recommend-repo` must answer the question the operator actually asks: "what should be added to which loadout?" The ledger should be grouped by loadout and include source path, target surface, decision, rationale, overlap/supersession, and provenance.

Required decision states:

- `recommend-add`: useful source behavior should become a new shared skill/instruction/pack and be wired into an existing loadout.
- `recommend-patch-existing`: useful source behavior should update an existing shared surface rather than creating a duplicate.
- `already-covered`: the source behavior is represented well enough; record the covering surface.
- `adapter-only`: source behavior belongs in runtime projection, hooks, bootstrap, or loadout-management rather than a user-facing loadout.
- `defer`: promising, but missing prerequisites or too risky now; record unblock condition.
- `reject`: intentionally not useful for Hermes; record why.

The ledger must be repo-pinned using `<owner/repo>::<candidate-or-source-path>` so a candidate name from one repo cannot merge with another repo's candidate of the same name.

For Superpowers-like skill repos, the expected output is not just "deep-coding candidate". It should explicitly list the skill surfaces, for example `subagent-driven-development`, `dispatching-parallel-agents`, and `using-git-worktrees` as recommended `deep-coding` additions or patches, while marking TDD/verification/debug basics as already covered or patch-existing.

## Claude/Codex parity requirement

Do not call a loadout synchronized because both runtimes have a folder or name. The onboarding command should classify each source-derived idea as:

- `shared`: should be represented in shared material and projected to both runtimes.
- `claude_only`: truly Claude Code-specific; document why.
- `codex_only`: truly Codex-specific; document why.
- `intentional_gap`: not portable now; document the gap and review trigger.

For hypothesis loadouts, the output should say whether a candidate is a new loadout, an enhancement to an existing loadout, or a rejected bundle.

## Prompting pattern for delegated planning

When using Claude Code to `/plan` this system, feed a large repo-aware braindump rather than a vague request. Include:

- repo path and branch;
- current source-list alias and number of repos;
- existing reports and queue docs;
- no-blind-copy/source-accounting rules;
- Claude/Codex parity requirement;
- target commands and artifact paths;
- verification commands;
- deliverable shape: build spec only, no implementation unless asked.

Keep the prompt in an ignored local task-file directory and the resulting build spec in public docs or another tracked product surface.

## Verification

Before reporting the command system or plan as ready, verify the source-list and loadout repo directly:

- Check the queue and per-repo plan through the maintainer source-registry tooling (not shipped publicly).
- Run the public gates:

```bash
python scripts/validate_loadouts.py
python scripts/smoke_clean_hermes_onboarding.py --json
git diff --check
```

If this is documentation-only, still run `python scripts/validate_loadouts.py` and `git diff --check`; say clearly what was skipped.

## Pitfalls

- Do not hard-code any single star list into executable logic. Store it as registry data in the maintainer source registry (not shipped publicly).
- Do not let Claude terminal history be the only copy of an architectural plan. Externalize it to a tracked plans lane.
- Do not migrate from upstream repos without an audit/synthesis record first.
- Do not let a recommendation stop at "not default" or "not a new loadout". If useful behavior exists, map it to an existing loadout/shared surface or explicitly reject/defer it.
- Do not create one skill per ingested repo. Keep repo-specific details in source reports; keep the reusable process in this class-level skill.
- Do not commit unless the operator explicitly approves the commit.
