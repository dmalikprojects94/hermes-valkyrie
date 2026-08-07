# Repo Surface Auditor

Classify what an onboarded repo actually contains, so adoption decisions are grounded in inventory, not vibes.

## When to use

After `github-source-intake` has registered a repo and you need a per-source ingestion report.

## Surface groups

Classify every meaningful upstream item into one of:

- skills
- commands
- agents
- hooks
- prompts
- MCP/server config
- runtime config
- design rules
- workflow doctrine
- scripts/tools
- full product engine

## Steps

1. Start a dated per-source ingestion report (`<OWNER>-<REPO>-INGESTION-YYYY-MM-DD.md`) from your ingestion-report template in your maintainer notes.
2. Inventory upstream files by surface group. Group meaningful surfaces; do not list every generated file.
3. Give every meaningful item a disposition label from the source provenance contract:
   `distilled-into-default`, `distilled-into-loadout`, `runtime-specific-adapter`, `repo-resident`, `superseded`, `deferred`, `rejected`.
4. Hand provenance decisions to `provenance-mapper` and parity decisions to `runtime-parity-mapper`.

## Hard rules

- **Reject heavy product engines by default.** Keep only narrow, transferable lessons; do not propose importing a full daemon/CLI/product runtime.
- **Never read or copy secrets** (`.env`, tokens, keys, credential files).
- Classification only — no migration. Adoption happens later through a migration task pack.

## Verification

```bash
python scripts/validate_loadouts.py
```

## Provenance

- Source: internal Hermes-operator design; see the maintainer utility-skill audit notes (utility skill 2) and the ingestion-report template (not shipped publicly).
- Disposition: repo-resident onboarding utility skill; not wired into `default`; available through the explicit `loadout-management` loadout.
- Notes: makes surface classification a repeatable step with fixed surface groups and disposition vocabulary.
