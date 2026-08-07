# Coding Discipline

Universal posture for writing code in this repo and any repo Hermes routes work into.

## Core principles

- **KISS** — pick the simplest mechanism that solves the problem.
- **DRY** — collapse genuine duplication, but only after the third repetition.
- **YAGNI** — do not write code for hypothetical future requirements.
- **Immutability first** — prefer pure functions, immutable data, and explicit state transitions over hidden mutation.

## Naming and structure

- Names should tell the reader what the thing is, not how it is built.
- One function = one responsibility. If you have to add a conjunction to describe it, split it.
- Keep modules small enough that a reader can hold the whole surface in their head.
- Surface boundaries belong at system edges (user input, external APIs, persistence). Internal code can trust internal code.

## Comments

- Default to no comments.
- Add a comment when the *why* is non-obvious: a hidden constraint, a workaround for a specific bug, a subtle invariant.
- Never describe what the code does — well-named identifiers already do that.
- Never reference current task, ticket, or caller. That context belongs in the commit message.

## Error handling

- Validate at the boundary, not at every internal call site.
- Do not add defensive code for situations that cannot happen.
- When something does fail, fail loudly with the original signal — do not swallow exceptions into silent fallbacks.

## Surface-change discipline

- Change behavior, not formatting, in a single diff.
- Refactor and feature-add are separate commits.
- If you discover a real cleanup opportunity, finish the task first, then propose the cleanup separately.

## Anti-patterns

- Wrapper functions that add nothing but indirection.
- Configuration knobs with one caller.
- Premature interfaces drawn around a single implementation.
- "TODO: clean this up later" comments without a tracked follow-up.

## Provenance

- Source: local Claude-OC-System default backbone doctrine plus internal Hermes-operator adaptation.
- Disposition: distilled-into-default.
- Notes: migrated as lean shared instruction text so Claude Code and Codex can inherit the same default intent.
