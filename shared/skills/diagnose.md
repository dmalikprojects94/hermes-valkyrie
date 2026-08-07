# Diagnose

Disciplined debugging loop for hard bugs and performance regressions. Distilled from Matt Pocock's `diagnose` skill. Strengthens the `/debug` command and the `silent-failure-hunter` and `build-error-resolver` agents.

## When to invoke

- Operator says "diagnose", "debug this", "why is this broken".
- Reports of incorrect output, exceptions, or performance regression.
- A failure mode is intermittent or doesn't reproduce on first attempt.

## Phases

### 1. Build a feedback loop

This is the skill. Everything else is mechanical once you have a fast, deterministic, agent-runnable pass/fail signal for the bug. Spend disproportionate effort here.

Loop construction options, roughly ordered:
1. Failing test at the seam closest to the bug.
2. Scripted HTTP call or CLI invocation against the running system.
3. Headless browser script for UI bugs.
4. Replay of a captured trace or payload.
5. Throwaway harness exercising the bug path in isolation.
6. Property / fuzz loop for "sometimes wrong" bugs.
7. Bisection harness for "appeared between two states" bugs.
8. Differential loop (old vs new, config A vs config B).
9. HITL script as last resort, when a human action is unavoidable.

For non-deterministic bugs, raise reproduction rate before declaring "no repro". A 50%-flake bug is debuggable; 1% is not.

If you genuinely cannot build a loop, stop. Say so explicitly, list what you tried, and ask the operator for environment access, captured artifacts, or permission to add temporary instrumentation. Do not proceed to hypothesise without a loop.

### 2. Reproduce

Run the loop. Confirm:
- The failure mode matches what the operator described, not a different failure that happens to be nearby.
- The bug is reproducible (deterministically or at a high enough rate).
- The exact symptom is captured so later phases can verify the fix.

### 3. Hypothesise

Generate 3-5 ranked hypotheses before testing any. Each must be falsifiable: state the prediction.

> "If X is the cause, then changing Y will make the bug disappear / changing Z will make it worse."

If you cannot state the prediction, the hypothesis is a vibe — discard or sharpen it. Surface the ranked list to the operator before probing — they often have domain knowledge that re-ranks instantly.

### 4. Instrument

Each probe maps to a specific prediction. Change one variable at a time.

- Prefer a debugger or REPL inspection over logs when available.
- Targeted logs at boundaries that distinguish hypotheses, not "log everything".
- Tag every debug log with a unique prefix (e.g. `[DEBUG-a4f2]`) so cleanup is a single grep.
- For performance regressions, measure first (baseline + harness or profiler), then bisect. Logs are usually wrong for perf.

### 5. Fix + regression test

Write the regression test before the fix, but only if there is a correct seam for it. A correct seam exercises the real bug pattern as it occurs at the call site. If no correct seam exists, that is itself a finding — note it and flag for architecture work.

1. Turn the minimised repro into a failing test.
2. Watch it fail.
3. Apply the fix.
4. Watch it pass.
5. Re-run the Phase 1 loop against the original scenario.

### 6. Cleanup + post-mortem

Before declaring done:
- Original repro no longer reproduces.
- Regression test passes (or absence of seam is documented).
- All tagged debug instrumentation removed.
- Throwaway prototypes deleted or moved to a clearly marked location.
- The hypothesis that turned out correct is stated in the commit/PR message.

Then ask: what would have prevented this bug? If the answer involves architectural change, hand off to `architecture-deepening`.

## Discipline

- Do not skip phases unless explicitly justified.
- Do not propose multiple fixes at once. Land one, verify, then move on.
- Verification evidence belongs in the Hermes reporting contract, not just the commit message.
