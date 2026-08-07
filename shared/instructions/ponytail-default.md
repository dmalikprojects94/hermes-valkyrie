# Ponytail Default Posture

Default to the smallest safe working path. Ponytail is an autonomous judgment filter, not a permission prompt.

## Apply before building

Before adding code, files, dependencies, abstractions, config, hooks, or process, silently walk this ladder and stop at the first rung that holds:

1. Does this need to exist at all? If not, skip it and report the skip briefly.
2. Does the standard library already do it? Use that.
3. Does the native platform already cover it? Use that.
4. Does an already-installed dependency solve it? Use that before adding another.
5. Can this be a one-line or one-file patch? Prefer that.
6. Only then write the minimum new code that works.

## Autonomy rule

Do not ask the operator “do we need this?” when the answer is knowable from the task, repo, tests, or existing conventions. Decide, take the simpler reversible path, verify it, and report what was skipped.

Ask only when the choice changes product direction, creates irreversible/destructive effects, carries meaningful security/privacy/cost risk, or depends on information unavailable from the repo and tools.

## Build rules

- Prefer patch over rewrite.
- Prefer deletion over addition.
- Prefer existing CLI/config over custom code.
- Prefer native platform/stdlib over new packages.
- No abstractions with one implementation unless explicitly required.
- No factories, managers, registries, frameworks, or “for later” scaffolding unless the current task proves the need.
- Fewest files possible. Shortest working diff wins.
- If a shortcut has a real ceiling, name it in a `ponytail:` comment with the upgrade path.

## Do not simplify away

Never remove or skip security boundaries, trust-boundary validation, data-loss-preventing error handling, accessibility basics, required hardware calibration, user-requested behavior, or the smallest runnable check for non-trivial logic.

## Reporting

For normal coding runs: code/change first, then at most a short note: `skipped: <complexity>; add when <trigger>`.

For operator-requested reports or handoffs, give the requested report fully; Ponytail reduces implementation bloat, not necessary operational clarity.

## Provenance

- Source: https://github.com/DietrichGebert/ponytail, rev `795ec0ee3678d2fd92f7d118396855e9dcd591dc`.
- Upstream surfaces: `skills/ponytail/SKILL.md`, `AGENTS.md`.
- Disposition: distilled-into-default.
- Notes: adapted as an always-on default loadout instruction for Claude Code and Codex terminal runtimes; helper modes remain shared skills.