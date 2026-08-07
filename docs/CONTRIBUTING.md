# Contributing

Thanks for your interest in improving the Terminal Loadout System.

## Ground rules

- Keep the default surface lean. Add specialty behavior in named loadouts, not
  the default backbone.
- Keep runtime-specific behavior in adapters; keep reusable behavior in shared.
- Prefer the smallest change that solves the problem. Delete before you add.
- Never commit secrets, real IDs, or absolute machine paths — use placeholders
  and `.env.example`.

## Development loop

1. Optional: `cp .env.example .env` and fill in your own values. No `.env` is
   needed for validation or sandbox materialization.
2. Make your change.
3. Validate the loadout repo (requires `python -m pip install pyyaml` once):

   ```bash
   python scripts/validate_loadouts.py
   ```

4. Confirm your diff is scoped to what you intended and free of whitespace
   damage:

   ```bash
   git diff --check
   ```

## Commit and pull-request conventions

- One topic per commit. Imperative subject under ~70 characters
  (`Add`, `Fix`, `Update`, `Refactor`, `Remove`, `Docs`, `Test`, `Chore`).
- The body explains *why*, not *what* — the diff already shows the what.
- One pull request per logical change. Include a short summary and a test plan.
- Stage files by name; avoid sweeping `git add -A` that can pull in local state.

## What not to include

- New dependencies without a stated reason and a license check.
- Speculative abstractions, config knobs with a single caller, or scaffolding
  "for later".
- Anything operator-specific or machine-specific: real IDs, absolute local
  paths, vault names, or personal workflow notes. The public tree must stay
  usable by anyone as-is.
