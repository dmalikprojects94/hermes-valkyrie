# Loadout Hypothesis Builder

Propose candidate loadouts **before** creating any directories. Prefer improving an existing loadout over inventing a new name.

## When to use

Synthesis has surfaced clusters and you want named loadout proposals grounded in source evidence.

## Process

The hypothesis automation for this workflow lives in the maintainer development workspace and does not ship with the public repo; follow the steps manually or with your own tooling. From the alias's synthesis clusters, write a hypotheses document (e.g. `docs/loadout-hypotheses/<alias>.md`) listing each candidate loadout.

## Each candidate carries

- name
- decision: `improve-existing`, `propose-new`, or `undecided`
- rationale
- evidence repos
- parity requirement

## Hard rules

- Use source evidence, not vibes.
- Prefer improving an existing loadout when a fit exists (`prefer_existing: true`).
- Create no loadout directories from this skill — hypotheses are documents only.
- `huashu-design` stays `undecided` until the operator decides whether it is standalone or part of `open-design` / `frontend-design`.

## Verification

Re-derive the hypotheses from the recorded evidence and confirm they are stable, then run:

```bash
python scripts/validate_loadouts.py
python scripts/smoke_clean_hermes_onboarding.py --json
```

## Provenance

- Source: internal Hermes-operator design; see the maintainer utility-skill audit notes (utility skill 7, not shipped publicly).
- Disposition: repo-resident onboarding utility skill; not wired into `default`; available through the explicit `loadout-management` loadout.
- Notes: backed by hypothesis tooling in the maintainer development workspace.
