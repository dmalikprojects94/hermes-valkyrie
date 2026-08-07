# Source List Onboarding

Use this when the operator points at any GitHub star list (or a repo inside one) and asks to integrate, classify, migrate, or save it for the Hermes coding-terminal loadout system.

> The source-registry automation for this workflow lives in the maintainer development workspace and does not ship with the public repo; follow the steps manually or with your own tooling.

Saved star lists live in the maintainer source registry (not shipped publicly) and are addressable by alias; the workflow accepts any other list URL too, so it is not bound to a single list.

The workflow covers these intake capabilities, whether run by hand or by your own tooling:

- Enumerate saved list aliases and resolve the repos inside a saved alias or any star-list URL (including parsing a saved HTML snapshot offline).
- Build a source-accounting plan for one repo.
- Report source-state counts and the next recommended repo, and compare reported revisions with live default-branch HEAD to flag stale reports.
- Create a dated live recheck report with machine-readable candidate metadata.
- Run one autonomous repo-to-loadout integration pass: source recheck, remote surface inventory, candidate extraction, default admission, loadout routing, and concrete integration plan files. Keep a stable checks-and-decisions ledger so repo resolution, surface inventory, default review, candidate routing, and project-reference decisions are reviewable in chat and git diff.
- Plan an audit pass without writing anything.
- Combine completed reports into patterns/clusters (synthesis).
- Propose candidate loadouts (hypotheses) before creating any.
- Write a migration task pack from known hypotheses or report-backed `source-candidates` blocks (never editing runtime surfaces).
- Route report-backed candidates to `default`, an existing named loadout, adapter-only work, or a proposed new loadout — always with an explicit default-loadout review, still editing nothing directly (admission planning).
- Produce a per-surface recommendation ledger from a deterministically selected source report (comparison), then a proposed-change doc whose meta names the exact selected report, class, and completeness.
- Prove the pipeline end-to-end without applying: select report, propose change in an isolated output root, dry-run the apply, confirm the repo gains no new dirty paths, and report the exact ingestion state.
- List every runtime path still needing authored content plus its evidence, as a dry-run task pack.

## Ingestion states and report lineage

Qualify every "ingested" claim with one state: `source-evidence-captured` → `source-accounted` → `comparison-ready` → `proposed-change-ready` → `dry-run-verified` → `content-authored` → `materialized`. Only `materialized` means a loadout actually changed.

A `live-recheck` report is **not** automatically comparison-ready. Select the comparison report deterministically (registry-pinned-if-comparison-ready → curated ingestion → live-recheck → richest candidate count); a freshly generated shallow recheck never shadows an older richer comparison-ready report. When pinning an exact report explicitly, fail loudly if it is not comparison-ready. Run the no-apply end-to-end smoke check before trusting a pointed-at repo.

The saved `claude-stack` queue document lives in the maintainer notes.

## Route check

Before launching a management runtime, verify routing with:

```bash
python scripts/resolve_route.py --runtime claude --request "audit this source list and map provenance"
python scripts/resolve_route.py --runtime codex --request "audit this source list and map provenance"
```

Expected result for source-list/provenance/migration-pack wording is `loadout-management`.

## Repo-resident utility skills

This umbrella skill delegates to focused utility skills. They are not wired into `default`; use the explicit `loadout-management` loadout when a Claude/Codex session should carry this whole update-management surface.

- `github-source-intake` — register a repo before analysis.
- `repo-surface-auditor` — classify repo contents into surface groups.
- `provenance-mapper` — decide inline vs source-map attribution.
- `runtime-parity-mapper` — gate every capability through Claude/Codex parity.
- `transfer-skill-builder` — build equivalent behavior across runtime gaps.
- `base-layer-guardian` — protect base/default; keep `default` small and route maintenance work to `loadout-management`.
- `source-synthesis` — combine reports into patterns/clusters.
- `loadout-hypothesis-builder` — propose loadouts before creating them.
- `migration-task-pack-writer` — convert hypotheses into non-applying task packs.
- `loadout-reset-verifier` — prove materialization resets stale files.
- `command-capability-parity-verifier` — verify exposed commands/skills per runtime.
- `loadout-development-closeout` — fixed closeout checklist and report.

Migration is **task-pack only**: the onboarding workflow never edits `loadouts/`, `shared/`, or `adapters/`.

## What this workflow does

This is an intake and classification workflow, not an auto-installer. It turns a promising GitHub repo into a source-accounted Hermes loadout decision.

## Workflow

1. Pick the list (saved alias or arbitrary URL) and resolve the repos in it.
   - Fast path for a single repo: run one full integration-plan pass and use the generated plan as the execution packet.
2. Check report freshness before trusting old reports.
3. For a stale or high-value repo, create a dated live report shell with `source-candidates` metadata.
4. Resolve the repo URL and inspect a concrete revision.
5. Create or update the per-source report from your ingestion-report template; keep the machine-readable `source-candidates` block current.
6. Inventory upstream files by type: skills, commands, agents, hooks, MCP, runtime config, prompts, docs, scripts, or full runtime.
7. Classify every meaningful upstream item with an explicit disposition label (e.g. adopted, distilled, rejected, deferred).
8. Compare candidates against the existing loadout inventory under `loadouts/` before proposing file changes. Prefer patching an existing loadout/skill target over creating a new loadout. If a source changes a loadout boundary, reason-to-exist, admission rule, exclusion rule, runtime posture, or verification expectation, update the loadout inventory documentation in the same pass.
9. Decide target surface autonomously; do not ask the operator when the evidence is enough:
   - `loadouts/<runtime>/Folder-Start/**` only for runtime baseline files that every Claude Code or Codex session needs.
   - `shared/instructions`, `shared/skills`, or `shared/packs` for distilled runtime-portable intent.
   - Claude-specific command, agent, hook, or MCP adapter surfaces for Claude-only behavior.
   - Codex baseline/config surfaces for Codex equivalents.
   - named loadout YAMLs for specialty routing.
10. Update source accounting in every pass: record in your maintainer notes the added-to-baseline date, inspected upstream version/revision, disposition, loadout targets, and canonical report links; what was taken, deferred, and rejected with affected/proposed loadouts; and any credits updates when the pass changes the live loadout baseline. Update `README.md` when the source changes the canonical source baseline, source navigation, scripts, loadout list, or onboarding procedure.
11. Run the admission review before writing task packs. This is the required default-loadout test. If the default review decision is `no-change`, do not add anything to default.
12. Decide default vs specialty:
   - `default` only if the item is broad, low-context, low-ceremony, and safe as inherited backbone.
   - `deep-coding`, `project-planner`, `frontend-design`, `open-design`, `research`, `media-video`, `loadout-management`, or another named loadout for opinionated or domain-specific behavior.
13. For existing loadout candidates, let the plan name the target loadout and exact additions. For unknown specialty candidates, create a proposed new-loadout task pack only; do not create or wire the loadout during onboarding unless the operator explicitly approves implementation.
14. Record Claude/Codex parity as synced, shared-only, acceptable gap, or missing.
15. Validate with `python scripts/validate_loadouts.py`, tests when relevant, and materialization for the affected runtime/loadout pairs.

## Saving a new list

Add another entry to the source registry with at least `alias`, `name`, and `url`. Optional fields: `queue_doc`, `priority_candidate`, `captured`, `notes`. The workflow then accepts the new alias with no code change.

## Claude Stack priority note

`ruvnet/ruflo` is the current priority repo in the `claude-stack` queue for onboarding/tooling analysis. Treat it as a full source pass, not a default-loadout import. It appears to contain Claude Code plugin surfaces, full CLI install behavior, agents, commands, skills, MCP/server behavior, hooks/daemon concepts, and Codex-related packages. Most useful material will probably belong in `deep-coding`, `project-planner`, or runtime adapters. Default should receive nothing unless a tiny distilled behavior passes the default admission rule.

## Output expected

Return a concise operator report with:

- source list (alias or URL), source repo, and inspected revision;
- what would go to `Folder-Start` for Claude/Codex;
- what would go to `default`;
- what would go to named loadouts;
- what is rejected/deferred;
- Claude/Codex parity status;
- files changed and validation output.

## Provenance

- Source: internal Hermes-operator design around the maintainer source registry and its saved source queues.
- Disposition: repo-resident onboarding tool; not wired into `default`.
- Notes: generalized from a Claude-Stack-only intake helper so any saved or ad-hoc GitHub star list becomes an explicit intake workflow rather than an informal browser bookmark.
