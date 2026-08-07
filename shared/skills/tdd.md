# TDD

Test-driven implementation with a red-green-refactor loop. Distilled from Matt Pocock's `tdd` skill. Strengthens the `/tdd` command and the `tdd-guide` agent.

## When to invoke

- Operator wants to build a feature or fix a bug test-first.
- Operator says "TDD", "red-green-refactor", "write the test first".
- A behavior change is being introduced into a covered surface.

## Philosophy

Tests verify behavior through public interfaces, not implementation details. Code can change entirely; tests should not. A good test reads like a specification — "user can checkout with valid cart" tells you what capability exists. Tests survive refactors because they don't care about internal structure.

Bad tests are coupled to implementation. The warning sign: a test breaks when you rename an internal function but behavior is identical. That test was testing structure, not behavior.

## Anti-pattern: horizontal slices

Do not write all tests first and then all implementation. That is horizontal slicing and produces tests that describe imagined behavior, not actual behavior. Tests become insensitive to real changes.

Correct approach: vertical slices via tracer bullets. One test -> one implementation -> repeat. Each test responds to what the previous cycle taught you.

## Workflow

### 1. Planning

Before any code:
- Confirm with the operator which interface changes are needed.
- Confirm which behaviors are most important to test. You cannot test everything; prioritise critical paths and complex logic.
- Identify opportunities for deep modules (small interface, deep implementation).
- List the behaviors to test, not the implementation steps.

### 2. Tracer bullet

Write one test that confirms one thing about the system. Run it red. Write the minimal code to pass. Run it green. This proves the path works end-to-end.

### 3. Incremental loop

For each remaining behavior:
- RED: write the next test. Watch it fail.
- GREEN: minimal code to pass. Watch it pass.

Rules:
- One test at a time.
- Only enough code to pass the current test.
- Do not anticipate future tests.
- Tests focus on observable behavior, not implementation.

### 4. Refactor

After all tests pass:
- Extract genuine duplication (not before the third repetition).
- Deepen modules — move complexity behind simple interfaces.
- Re-run tests after each refactor step.

Never refactor while RED. Get to GREEN first.

## Per-cycle checklist

- Test describes behavior, not implementation.
- Test uses the public interface only.
- Test would survive an internal refactor.
- Code is minimal for the current test.
- No speculative features added.

## Hermes interaction

- Report the number of red-green cycles completed in the Hermes summary.
- If a test had to be deleted or rewritten mid-cycle, surface that — it usually signals the original test was coupled to implementation.
