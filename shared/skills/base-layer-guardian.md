# Base Layer Guardian

Protect the always-on base layer. Decide whether a capability belongs in **base**, **default**, or a **specialty loadout** — and keep `default` small.

## When to use

Whenever a capability's destination is being decided, especially if someone proposes adding it to `default`.

## Destination rules

- **Base** — runtime baseline every session needs. Lives in `loadouts/<runtime>/Folder-Start/**`. Add here only for true runtime baseline.
- **Default** — broad, low-context, low-ceremony, safe inherited backbone. Expensive; admit sparingly.
- **Specialty loadout** — the normal destination for strong opinions or domain-specific behavior.

## Always-on base files/surfaces

- runtime `Folder-Start` baseline files
- shared core instructions
- minimal default skills
- command-inventory surfaces
- Stop-hook / reporting lifecycle rules

Every materialized loadout must include the base files. Confirm this after materialization.

## Default admission test

Admit to `default` only if **all** hold:

1. Broad — useful across most work, not one domain.
2. Low-context — cheap to carry every session.
3. Low-ceremony — no heavy setup or multi-step ritual.
4. Safe — no destructive or surprising behavior as inherited backbone.

If any fails, route to a specialty loadout.

Before any source-backed migration task pack, run an explicit admission review of every report-backed candidate. (The admission-plan automation lives in the maintainer development workspace and does not ship with the public repo; do the review manually or with your own tooling.)

This is the default-loadout admission check. If the default review decision is `no-change`, default receives nothing. If a candidate targets an existing specialty loadout, the plan should identify that loadout and list the proposed additions. If no existing loadout fits, the plan should propose a new named loadout task pack.

## Materialization checks

```bash
python scripts/apply_loadout.py --runtime claude --loadout default --output-root /tmp/base-check --format json
python scripts/apply_loadout.py --runtime codex --loadout default --output-root /tmp/base-check --format json
```

Confirm each affected loadout still carries base files after the change.

## Verification

```bash
python scripts/validate_loadouts.py
```

## Provenance

- Source: internal Hermes-operator design; see the maintainer utility-skill audit notes (utility skill 6) and the loadout synchronization contract (not shipped publicly).
- Disposition: repo-resident onboarding utility skill; not wired into `default`; available through the explicit `loadout-management` loadout.
- Notes: keeps the backbone lean and base files present everywhere.
