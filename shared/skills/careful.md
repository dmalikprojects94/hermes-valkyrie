# Careful

Guardrail posture for destructive or irreversible operations.

## When this skill applies

Before any command that:
- deletes files, directories, branches, tags
- drops, truncates, or alters database tables
- force-pushes, hard-resets, or rewrites git history
- kills processes, removes containers, or destroys infrastructure
- overwrites uncommitted work
- bypasses safety checks (`--no-verify`, `--force`, `rm -rf`)

## Pre-flight checklist

1. **Reversible?** If yes, proceed with normal verification. If no, stop and confirm.
2. **Blast radius?** Local file, current branch, shared branch, production. The wider it goes, the more deliberate the confirmation.
3. **Has the operator authorized this scope?** A prior `yes` for one destructive op does not authorize a different one.
4. **Is there a safer alternative?** Soft delete, dry run, staged rollout, reversible flag. Prefer the safer path when the goal is the same.

## Action protocol

- State the destructive action and its blast radius before executing.
- For genuinely irreversible operations, request explicit confirmation referencing the *specific* artifact (branch name, file path, table name).
- After the operation, verify the intended end state and the absence of collateral damage.

## Anti-patterns

- Using destructive shortcuts to make an obstacle "go away" rather than diagnosing the root cause.
- Treating `rm`, `git reset --hard`, or `DROP` as routine.
- Skipping hooks because they failed — investigate why instead.
- Cleaning up "unfamiliar" files or branches before checking what they are.

## When the hook layer enforces this

The `suggest-compact` hook handles compaction nudges; destructive command guardrails are enforced via runtime hooks where available. This skill is the *posture*; the hook is the *enforcement*.

## Provenance

- Source: local Claude-OC-System default skill surface plus internal Hermes-operator adaptation.
- Disposition: distilled-into-default.
- Notes: migrated as a shared runtime-portable skill for the solidified default loadout.
