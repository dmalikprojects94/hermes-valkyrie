# Provenance Mapper

Decide where attribution lives for every adopted piece of upstream work. No untraceable text reaches a runtime surface.

## When to use

After `repo-surface-auditor` has classified items and some are headed for adoption.

## Two attribution modes

- **Inline `## Provenance` block** — use for *safe frame files* where a provenance section does not change runtime behavior (skills, instructions, packs, adapters, docs).
- **Source-map / project-tree documentation** — use for *behavior-sensitive files* where inline provenance would pollute runtime behavior. Keep attribution in your maintainer source notes (the ingestion report and the source-matrix ledger) instead.

## Exact inline block shape

```md
## Provenance

- Source: https://github.com/<owner>/<repo> `<path/in/repo>` at `<revision-or-date>`
- License: <license or unknown>
- Disposition: distilled-into-loadout `<loadout>` / distilled-into-default / runtime-specific-adapter
- Notes: <what changed during Hermes adaptation; note if conceptual inspiration vs direct text>
```

Fully internal files use:

```md
## Provenance

- Source: internal Hermes-operator design
- Notes: no external source material used
```

## Hard rules

- Every adopted feature or text block must be traceable to **repo, path, revision, license, and disposition**.
- **Forbid untraceable copied text.** If a block cannot be traced, do not adopt it.
- When inline provenance would hurt runtime behavior, document attribution in source docs rather than inlining it.
- Every migration task pack must carry exact provenance text or an exact doc-citation path.

## Verification

```bash
python scripts/validate_loadouts.py
```

## Provenance

- Source: internal Hermes-operator design; see the maintainer utility-skill audit notes (utility skill 3) and the source provenance contract (not shipped publicly).
- Disposition: repo-resident onboarding utility skill; not wired into `default`; available through the explicit `loadout-management` loadout.
- Notes: operationalizes the inline-vs-docs provenance decision.
