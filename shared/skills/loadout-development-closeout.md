# Loadout Development Closeout

Finish any onboarding/development pass cleanly with a fixed verification checklist and report.

## When to use

At the end of every substantial onboarding or loadout-development pass.

## Required checks

```bash
python scripts/validate_loadouts.py
python scripts/smoke_clean_hermes_onboarding.py --json
# materialization for affected runtime/loadout pairs:
python scripts/apply_loadout.py --runtime claude --loadout <name> --output-root /tmp/closeout --format json
python scripts/apply_loadout.py --runtime codex  --loadout <name> --output-root /tmp/closeout --format json
git diff --check
git status --short
```

## Required report

Report back:

- files changed
- verification output (what ran, what it returned)
- provenance/parity gaps still open
- **whether migration happened** (for non-migrating passes, state "no migration")

## Hard rules

- Never report closeout without the actual command output or an explicit blocker.
- Include both Claude and Codex materialization when the change affects shared skills or loadout routing.
- Use `loadout-management` for source/update management closeout unless the task explicitly targeted a different loadout.

## Provenance

- Source: internal Hermes-operator design; see the maintainer utility-skill audit notes (utility skill 12, not shipped publicly).
- Disposition: repo-resident onboarding utility skill; not wired into `default`; available through the explicit `loadout-management` loadout.
- Notes: standard closeout for onboarding/development work.
