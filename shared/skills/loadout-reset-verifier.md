# Loadout Reset/Switch Verifier

Prove that materializing a loadout resets stale files from a previous loadout in the same output root.

> Scope: this is **launch/materialization-time** switching. Do not claim live in-session loadout switching unless that is separately implemented and tested.

## When to use

After any loadout or shared-skill change, to confirm switching does not leave stale files behind.

## Procedure

1. Apply loadout A to a temp output root.
2. Insert a stale file under a managed directory (e.g. `skills/stale/SKILL.md`).
3. Apply loadout B to the same output root.
4. Confirm the stale file is removed.
5. Confirm the generated command inventory matches loadout B.
6. Repeat independently for Claude and Codex roots.

## Commands

```bash
python scripts/validate_loadouts.py
python scripts/smoke_clean_hermes_onboarding.py --json
python scripts/apply_loadout.py --runtime claude --loadout frontend-design --output-root /tmp/loadout-reset-proof --format json
python scripts/apply_loadout.py --runtime claude --loadout default --output-root /tmp/loadout-reset-proof --format json
python scripts/apply_loadout.py --runtime codex --loadout research --output-root /tmp/loadout-reset-proof --format json
python scripts/apply_loadout.py --runtime codex --loadout default --output-root /tmp/loadout-reset-proof --format json
```

## How reset works

`apply_loadout` clears managed paths (skills, commands, agents, rules, hooks, mcp, memories, inventory, manifest) for the target runtime before re-materializing, so files from a prior loadout inside those managed directories are removed.

## Provenance

- Source: internal Hermes-operator design; see the maintainer utility-skill audit notes (utility skill 9, not shipped publicly).
- Disposition: repo-resident onboarding utility skill; not wired into `default`; available through the explicit `loadout-management` loadout.
- Notes: backed by reset-behavior tests in the maintainer development workspace.
