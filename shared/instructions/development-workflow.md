# Development Workflow

The execution spine for non-trivial work: research → plan → TDD → verify → review.

## 1. Research

- Read the relevant code before proposing a change.
- Locate the closest existing pattern. Match it unless there is a reason to diverge.
- Pull in only the context required for this change; resist whole-repo dumps.

## 2. Plan

- Restate the request in one sentence.
- Decompose into the smallest sequence of verifiable steps.
- Name the stop condition: what evidence will prove this is done?
- Flag risks, dependencies, and reversibility *before* writing code.

## 3. TDD (when applicable)

- Write the failing test first when the change has a clear behavioral contract.
- For exploratory or UI changes where TDD is awkward, replace it with a fast feedback loop (run-edit-observe).
- Either way: small change, observe outcome, then iterate.

## 4. Verify

- Run the narrowest meaningful check first (unit test, single command, single page load).
- Expand verification only after the narrow check passes.
- Evidence beats assertion: tool output, screenshots, log lines, or test results — not "should be fine."

## 5. Review

- Re-read the diff before declaring complete.
- Check that you did not introduce dead code, drift in unrelated files, or weakened guarantees.
- Confirm scope: the diff should match what was requested.

## Loop discipline

Each pass through the loop should be small enough that a regression points at exactly one change. If a step requires more than a few minutes of work without verification, break it down further.

## When to break the spine

- For trivial fixes (typo, single-line edit, doc tweak), collapse to: plan → execute → verify in one breath.
- For research-only requests, the deliverable is the synthesis, not code.
- For destructive or irreversible operations, the plan step is the most important; do not shortcut it.

## Provenance

- Source: local Claude-OC-System default backbone doctrine plus internal Hermes-operator adaptation.
- Disposition: distilled-into-default.
- Notes: migrated as lean shared instruction text so Claude Code and Codex can inherit the same default intent.
