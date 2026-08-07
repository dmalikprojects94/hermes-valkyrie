# Prototype

Throwaway code that answers a question. Distilled from Matt Pocock's `prototype` skill.

## When to invoke

- Operator says "prototype this", "let me play with it", "try a few designs", "sanity-check this state model".
- A decision needs evidence that prose cannot provide.
- Before committing to a data model, state machine, or UI direction.

## Pick a branch

Identify which question is being answered.

- **"Does this logic or state model feel right?"** -> build a tiny interactive terminal app that pushes the model through cases that are hard to reason about on paper.
- **"What should this look like?"** -> generate several radically different UI variations on a single route, switchable via a URL search param.

If the question is genuinely ambiguous and the operator isn't reachable, default to whichever branch matches the surrounding code (backend module -> logic; page or component -> UI) and state the assumption at the top of the prototype.

## Rules that apply to both branches

1. **Throwaway from day one, clearly marked as such.** Locate prototype code close to where it will be used, but name it so a casual reader can see it is a prototype.
2. **One command to run.** Whatever the project's existing task runner supports. The operator must be able to start it without thinking.
3. **No persistence by default.** State lives in memory. If a DB is unavoidable, use a scratch path with a clear "wipe me" name.
4. **Skip the polish.** No tests, no error handling beyond what makes the prototype runnable, no abstractions. Learn fast, delete fast.
5. **Surface the state.** Print or render the full relevant state after every action.
6. **Delete or absorb when done.** Once the prototype answers its question, fold the validated decision into real code or delete it. Do not leave it rotting.

## When done

The answer is the only thing worth keeping. Capture it in a durable artifact (commit message, ADR, issue, or `NOTES.md` next to the prototype) along with the question it answered.

## Hermes interaction

- Prototypes ship as part of a coding loadout. Report the prototype path and the question it answers in the Hermes summary.
- A prototype that survives the session without being absorbed or deleted is a Hermes follow-up item, not a success.
