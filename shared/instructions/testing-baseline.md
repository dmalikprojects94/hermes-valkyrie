# Testing Baseline

Soft floor for tests across loadouts. Specialty loadouts can raise the bar.

## TDD posture

- When the change has a clean behavioral contract, write the failing test first.
- When the change is exploratory, scaffolding, or UI-shaped, replace TDD with a tight feedback loop and add tests once the shape stabilizes.
- A test that fails for the right reason is worth more than five tests that pass for the wrong reason.

## Test types and where each belongs

- **Unit** — pure logic, branching, edge cases. Fast, isolated, deterministic.
- **Integration** — real boundaries: real database, real filesystem, real HTTP. Mock only what is genuinely out of reach (paid APIs, slow third-party services).
- **End-to-end** — full system through the entry point. Use sparingly; treat as smoke coverage.
- **Property / fuzz** — when the input space is wide or the invariants are hard to enumerate by hand.

## Default expectations

- Every new branch in behavior gets at least one test that fails without the change and passes with it.
- Every fixed bug gets a regression test that reproduces the original failure.
- No required coverage percentage — coverage of the *behavior* matters more than coverage of the *lines*.

## What not to test

- Trivial getters, setters, and pass-through wrappers.
- Framework internals you do not own.
- Implementation details that will change next sprint without a behavior change.

## Test quality

- Test names describe the behavior, not the function being called.
- One assertion per concept; multiple assertions per test only when they form one logical check.
- No shared mutable state between tests.
- Failing tests must point at the cause, not just the symptom.

## When tests get in the way

- If a test is asserting the wrong thing, fix the test, do not skip it silently.
- Skipped tests need a tracked follow-up; do not let `xfail` rot.

## Provenance

- Source: local Claude-OC-System default backbone doctrine plus internal Hermes-operator adaptation.
- Disposition: distilled-into-default.
- Notes: migrated as lean shared instruction text so Claude Code and Codex can inherit the same default intent.
