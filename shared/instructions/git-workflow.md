# Git Workflow

Commit and PR conventions for any repo Hermes routes work into.

## Commit messages

- One topic per commit. If the message uses "and," consider splitting.
- Subject line under 70 characters, imperative mood ("Add", "Fix", "Refactor", not "Added", "Fixes").
- Body explains the *why*, not the *what* — the diff already shows the what.
- Reference issues or tickets only when the link adds context the future reader will need.

Use a leading verb that matches the change:
- `Add` — net-new feature or file.
- `Update` — enhancement to existing behavior.
- `Fix` — bug fix.
- `Refactor` — structure change with no behavior change.
- `Remove` — deletion of dead or deprecated code.
- `Docs` — documentation-only change.
- `Test` — test-only change.
- `Chore` — build, deps, tooling.

## Staging discipline

- Stage files by name. Avoid `git add -A` or `git add .` — they sweep up secrets, build artifacts, and unrelated work.
- Re-read `git status` and `git diff --staged` before committing.
- Never commit `.env`, credential files, or generated artifacts unless explicitly asked.

## Commit readiness

Before each commit, confirm:
- No secrets or credentials.
- Tests pass (or the commit is explicitly marked WIP).
- The diff matches the commit message.
- No debug prints, commented-out code, or scratchpad files.

## PR workflow

- One PR per logical change. Split aggressively rather than bundling.
- PR title mirrors the lead commit's subject.
- PR body has: Summary (1-3 bullets), Test plan (checklist), and any migration notes.
- Link related PRs and issues in the body, not the title.

## Destructive operations

- Never force-push to shared branches (main, release branches) without explicit operator approval.
- Never `git reset --hard` over uncommitted work without confirming.
- Never bypass hooks (`--no-verify`, `--no-gpg-sign`) unless the operator asks for it.

## Rewriting history

- Rebase only on private branches before opening the PR.
- After review starts, prefer additive commits over force-push rewrites.

## Provenance

- Source: local Claude-OC-System default backbone doctrine plus internal Hermes-operator adaptation.
- Disposition: distilled-into-default.
- Notes: migrated as lean shared instruction text so Claude Code and Codex can inherit the same default intent.
