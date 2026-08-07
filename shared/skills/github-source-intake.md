# GitHub Source Intake

Register a GitHub repo or source-list alias **before** any audit or migration work. Intake is accounting, not adoption.

## When to use

the operator points at a repo, a GitHub URL, or a saved star-list alias and wants it onboarded into the loadout system.

## Inputs accepted

- `owner/repo`
- a full GitHub repo URL
- a saved source-list alias (e.g. `claude-stack`)
- a GitHub star-list URL

## Steps

1. Resolve and record, before reading source files in depth: source URL, inspected revision (commit/tag/branch/date), license, repo type, and the source-list alias when one applies.
2. Check the repo's current standing in the maintainer source registry (not shipped publicly) first. (The status automation lives in the maintainer development workspace; check manually or with your own tooling.)
3. Persist structured state without clobbering operator decisions.
4. Point the operator at README/source references and add the repo row to your source-matrix ledger; if the pass adds or materially updates skills/source surfaces, add the matching entry to your source update ledger in the same change.
5. Hand off to `repo-surface-auditor` for classification.

## Hard rules

- **No migration during intake.** Do not copy upstream files into `shared/`, `loadouts/`, `adapters/`, or `Folder-Start`.
- Never read or copy secrets.
- Record source accounting even when nothing will be adopted.
- State writes are idempotent; operator/manual namespaces are preserved.

## SOURCE-MATRIX entry rules

Each onboarded repo gets one row: repo slug, source URL, inspected revision, license, repo type, and current disposition (start at `unvisited` / `reported-no-migration`). Update the row as state changes; never delete history silently. Keep a shorter GitHub skill/source update ledger alongside it and update it whenever this repo pass creates or materially patches local skills or source-derived surfaces.

## Verification

Re-check the alias status in the source registry, then run:

```bash
python scripts/validate_loadouts.py
```

## Provenance

- Source: internal Hermes-operator design; see the maintainer utility-skill audit notes (utility skill 1) and the source provenance contract (not shipped publicly).
- Disposition: repo-resident onboarding utility skill; not wired into `default`; available through the explicit `loadout-management` loadout.
- Notes: makes source registration an explicit, repeatable step ahead of analysis.
