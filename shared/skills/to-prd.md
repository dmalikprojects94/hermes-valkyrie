# To PRD

Turn the current conversation context into a PRD. Distilled from Matt Pocock's `to-prd` skill, adapted to Hermes.

## When to invoke

- Operator says "make this a PRD", "write the PRD", "publish this as a PRD".
- A conversation has converged on a feature and now needs a durable artifact.
- A planning route is closing out and the next runtime needs a clean spec.

## Discipline

- Do not interview the operator. The point of `to-prd` is to synthesize what is already in context, not to grill further. If the conversation hasn't reached convergence yet, use `grill-with-docs` or `grill-me` first.
- Use the project's domain vocabulary throughout. If a `CONTEXT.md` glossary exists, prefer those terms.
- Sketch the major modules that will need to be built or modified. Actively look for opportunities to extract deep modules that can be tested in isolation. Confirm with the operator that the module shape matches expectations and which modules they want tests for.

## PRD template

```
## Problem statement
The problem from the user's perspective.

## Solution
The solution from the user's perspective.

## User stories
A long, numbered list. Each story in the form:
1. As an <actor>, I want a <feature>, so that <benefit>.

Cover all aspects of the feature.

## Implementation decisions
- Modules to build or modify.
- Interfaces that will be touched.
- Architectural decisions.
- Schema changes, API contracts, specific interactions.

Do not embed specific file paths or code snippets — they go stale.
Exception: a state machine, schema, or type shape from a prototype may be inlined if it encodes a decision more precisely than prose can.

## Testing decisions
- What makes a good test (behavior, not implementation).
- Which modules will be tested.
- Prior art in the codebase for similar tests.

## Out of scope
Things explicitly excluded from this PRD.

## Further notes
Anything else worth recording.
```

## Publishing

Once the PRD is drafted, publish it to the configured issue tracker (if any) with a `ready-for-agent` triage label, or hand the PRD path back to Hermes as the canonical artifact for the next runtime to pick up. If no issue tracker is configured, write the PRD as a markdown file in the working tree and surface the path in the Hermes report.
