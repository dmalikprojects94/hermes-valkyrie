# Autonomous Repo Integration

Use this when the operator points at a GitHub repo and wants the loadout system to decide what to integrate without another manual planning discussion.

## One-pass process

The integration-plan automation for this workflow lives in the maintainer development workspace and does not ship with the public repo; follow the steps manually or with your own tooling.

Run one integration-plan pass for the target repo (naming the source-list alias it came from) and produce two separate dated artifacts:

- a dated source recheck report in your maintainer source notes
- a dated autonomous integration plan under `docs/integration-plans/`

Every integration plan includes a readable `## Checks and decisions ledger` with stable check cards for repo resolution, surface inventory, default-loadout review, candidate routing, and project-reference follow-up. Also produce an operator-summary block that is suitable to paste back to the operator.

## What the process does

1. Resolve the GitHub repo and inspect the live default-branch revision.
2. Pull the remote repo tree through `gh api` and classify surfaces:
   - Claude commands
   - Claude agents
   - Claude hooks
   - skills / SKILL.md files
   - MCP files
   - docs
   - runtime config
   - scripts
   - generic files to leave upstream
3. Generate source-candidate metadata from repo metadata and surfaces.
4. Run the default-loadout admission check.
5. Route each candidate autonomously:
   - `default` only when explicitly default-admitted
   - existing named loadout when the target is clear
   - adapter-only work into `loadout-management`
   - proposed new loadout when no existing loadout fits
6. Produce a concrete integration plan with:
   - upstream surface inventory
   - leave/do-not-integrate list
   - default review
   - exact loadout actions
   - checks and decisions ledger
   - documents to update
   - verification commands
   - rollback note

## Checks and decisions ledger

Use check-card blocks for important checks so the result is readable in chat and still reviewable in git diff:

```markdown
### repo-resolution — pass
- Evidence: <repo @ revision>
- Decision: analyze live default branch
- Next: preserve source report and integration plan

### surface-inventory — pass
- Evidence: <path count + surface counts>
- Decision: distill portable behavior only
- Next: leave generic runtime/source files upstream

### default-loadout-review — pass
- Evidence: <default additions or none>
- Decision: no-change/extend-default
- Next: change default only with explicit admission

### candidate-routing — pass
- Evidence: <candidate -> decision -> target>
- Decision: autonomous route to adapter/existing/new loadout
- Next: create migration task packs

### project-reference — required
- Evidence: docs/projects/<project-slug>.md convention
- Decision: create/update durable project reference
- Next: link reports, plans, task packs, verification
```

Add extra cards for unusual blockers, security findings, or manual exceptions. Do not include secrets, tokens, or private IDs.

## Three stages: analysis → prepare → apply

The canonical operator path is the three-stage adopt-source contract (documented in the
maintainer pipeline notes). Integration planning and migration planning are helpers
underneath it. Keep operator language on the three stages and never report unqualified
"ingested":

- **analysis** — read-only. Resolve/generate the surface inventory, classify, and route. No live
  or staged writes; `live_repo_clean_after` stays `true`.
- **prepare** — write a reviewable staging bundle into an isolated `--output-root` only. Every op
  is unapproved with empty content, so the bundle is **not applyable**.
- **apply** — consume only an approved, attributed, reviewer-stamped proposed-change doc, behind
  the full apply gate (allowlist, clean-tree, post-apply verification with rollback).

## Mechanics-complete vs trusted-analysis-complete

These are two different bars, and only the second is allowed to gate a `prepare`:

- **mechanics-complete** — the CLI ran: it enumerated paths, classified each surface by
  path/extension, and emitted routing rows with `evidence`, `recommendation_state`, candidate
  `target_loadout`/`target_surface`. This is inventory/routing proof. It may include best-effort
  body reads when GitHub content is available, but any row with `body_read: false` or
  `behavior_extracted: false` remains path-counting and is not trustworthy for adoption by itself.
  (See the "Mechanical vs. human verdicts" split in the classification vocabulary.)
- **trusted-analysis-complete** — the body of every meaningful upstream surface has been read by
  the CLI or a human/agent and the row carries the normalized behavior fields below. Only trusted
  behavior rows are allowed to conclude "this maps to / duplicates / is missing from loadout X".

## Normalized behavior row (trusted analysis)

For every meaningful upstream surface (each skill/SKILL.md, command, agent, hook with real
behavior), enrich the mechanical routing row into a behavior row carrying at least:

- source path
- trigger / intent (when it fires, what the user relies on) — read from the body, not the path
- tools / dependencies it invokes
- workflow summary (what it actually does, 1–2 lines)
- candidate local destination (loadout + surface)
- overlap / dedupe status against existing local surfaces
- disposition (a recommendation state from `classification-vocabulary.md`)
- confidence (how sure the disposition is, given the evidence read)
- evidence (non-empty path(s) actually read)

Rule: **every meaningful upstream surface must appear as its own child row with non-empty
evidence paths before any broad repo-level bucket** (e.g. "skills +14") is trusted. A bucket
count with unread children is mechanics-complete only.

## Ready for prepare

A repo is ready to move from analysis to prepare when:

- every meaningful upstream surface has a behavior row with non-empty evidence,
- each `recommend-add` / `recommend-patch-existing` row has a concrete candidate destination and a
  disposition with stated confidence, and
- adapter-only / reference-only / process-only rows are explicitly marked **analysis-only / no
  implementation** and excluded from the human-facing add/patch queue.

A row is **analysis-only / no implementation** when its disposition is `adapter-only`,
`repo-resident-reference`, runtime-parity, source/catalog, or otherwise process-only: it stays
visible in the routing table for accounting, but it produces no add/patch suggestion and is never
materialized.

## Reversible proof loop

To prove the pipeline without risking the canonical repo:

1. Start from a clean tree (`git status` clean; record the baseline commit).
2. **analysis** into an isolated temp root — read-only, confirm `live_repo_clean_after: true`.
3. **prepare** into `--output-root /tmp/...` — staging bundle only, still not applyable.
4. **apply** only an approved sample content packet, into an isolated branch / worktree / temp
   output root — never the live loadout tree.
5. Run validation (`validate_loadouts.py`, targeted tests, apply-gate verification).
6. Rewind/cleanup: discard the temp root / branch; re-confirm the canonical tree is clean.

## Hard rules

- Do not bulk-import upstream Claude Code systems.
- Do not import full runtime scaffolding unless it is a runtime adapter task.
- Leave generic source files upstream unless a behavior maps cleanly to Hermes shared skills or adapter surfaces.
- Keep `default` lean. A no-change default review means default receives nothing.
- Adapter-only, runtime-parity, source/catalog, and process-only candidates are **not** human-facing
  implementation suggestions under `loadout-management`. They are analysis-only routing rows; do not
  turn them into add/patch work for an operator. `loadout-management` is a process loadout, not an
  adoption target.
- Design / taste / UX skills route to `frontend-design` (then `open-design`), never to
  `loadout-management`.
- Plans are allowed to make routing decisions by themselves; implementation still happens through task packs and verified edits.

## Follow-up

After reviewing the generated integration plan, write a migration task pack for each admitted candidate (see `migration-task-pack-writer`).

Then verify implementation work with:

```bash
python scripts/validate_loadouts.py
python scripts/smoke_clean_hermes_onboarding.py --json
python scripts/apply_loadout.py --runtime claude --loadout <target> --output-root /tmp/loadout-integration-check --format json
python scripts/apply_loadout.py --runtime codex --loadout <target> --output-root /tmp/loadout-integration-check --format json
```

## Provenance

- Source: the operator's requested autonomous GitHub-repo-to-loadout integration pipeline.
- Disposition: repo-resident management skill; use through `loadout-management`, not `default`.
