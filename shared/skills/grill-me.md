# Grill Me

Relentless one-question-at-a-time interview to align on a plan before execution. Distilled from Matt Pocock's `grill-me` skill. Lighter counterpart to `grill-with-docs` (which adds `CONTEXT.md` / ADR awareness for code work).

## When to invoke

- Operator says "grill me", "interview me", "stress-test this plan".
- A plan is being formed for non-code or pre-code work where domain docs are not yet relevant.
- Decisions need to be resolved one at a time rather than picked off a menu.

## How to run it

1. Walk down each branch of the decision tree.
2. Resolve dependencies between decisions one at a time.
3. Ask one question, wait for the operator's answer, then move to the next.
4. For each question, propose your recommended answer. The operator can accept, override, or push back.
5. If a question can be answered by exploring the codebase or an existing artifact, explore instead of asking.

## When to stop

- The operator says "we're done", "good enough", "stop grilling".
- Every remaining open question is genuinely outside the scope of the current task.
- The plan is concrete enough to hand off (deliverables, scope edges, verification approach are all named).

## Hermes interaction

- The output of a grilling session is a tightened plan, not just a chat transcript. End with a short consolidated summary so Hermes can carry it forward.
- If the grilling surfaces a code dependency, switch to `grill-with-docs` instead and continue there. Note the switch in the summary.
