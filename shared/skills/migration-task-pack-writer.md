# Migration Task-Pack Writer

Convert an approved hypothesis into an implementation packet. Task packs **propose** runtime edits; they never apply them.

## When to use

A hypothesis is approved and you need a concrete, reviewable implementation plan.

## Process

The admission/migrate-plan automation for this workflow lives in the maintainer development workspace and does not ship with the public repo; follow the steps manually or with your own tooling. Run the admission review for the alias, then derive the task pack for the approved hypothesis and write it under `docs/migration-task-packs/<alias>/<name>.md`.

Packs are append-only unless a replacement is explicitly intended.

Use the admission plan first. It is allowed to make autonomous routing decisions: default no-change, extend an existing loadout, adapter-only management work, or create a proposed new loadout. The task pack then captures the exact additions and verification commands.

## Each pack includes

- source reports used
- files to create/modify (proposals)
- provenance text or exact doc-citation path
- Claude mapping
- Codex mapping
- parity status
- verification commands
- rollback plan

## Hard rules

- Task-pack writing never edits `loadouts/`, `shared/`, or `adapters/` directly; it only writes under `docs/migration-task-packs/`.
- Every pack carries exact provenance text or an exact citation path (see `provenance-mapper`).
- Applying a pack is a separate, human-initiated step.

## Verification

Re-derive the pack from the recorded hypothesis and confirm it is stable, then run:

```bash
python scripts/validate_loadouts.py
python scripts/smoke_clean_hermes_onboarding.py --json
```

## Provenance

- Source: internal Hermes-operator design; see the maintainer utility-skill audit notes (utility skill 8, not shipped publicly).
- Disposition: repo-resident onboarding utility skill; not wired into `default`; available through the explicit `loadout-management` loadout.
- Notes: backed by migrate-plan tooling in the maintainer development workspace.
