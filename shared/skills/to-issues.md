# To Issues

Break a plan, spec, or PRD into independently-grabbable issues using tracer-bullet vertical slices. Distilled from Matt Pocock's `to-issues` skill, adapted to Hermes's runtime-agnostic posture (the actual issue tracker is configured outside this skill).

## When to invoke

- Operator says "break this into issues", "make tickets", "split this for AFK agents".
- A plan or PRD exists and needs to be sliced into work units.
- After `to-prd` produced a PRD that now needs implementation slices.

## Prerequisites

- An issue tracker is configured for the repo (GitHub Issues, GitLab Issues, local markdown, or Linear). If unclear, ask the operator before proceeding.
- The plan or PRD exists in the conversation context or can be referenced by path / URL.

## Process

### 1. Gather context

Work from whatever is already in the conversation. If the operator passes a reference (issue number, URL, or path), fetch it and read the full body.

### 2. Explore the codebase (optional)

If you have not already explored the codebase for this work, do so to ground titles and descriptions in the project's domain vocabulary.

### 3. Draft vertical slices

Each issue is a thin vertical slice that cuts through all integration layers end-to-end, not a horizontal slice of one layer.

Slices are either **HITL** (requires a human decision mid-flight) or **AFK** (can be implemented and merged without human interaction). Prefer AFK where possible.

Rules:
- Each slice delivers a narrow but complete path through every layer (schema, API, UI, tests).
- A completed slice is demoable or verifiable on its own.
- Prefer many thin slices over few thick ones.

### 4. Quiz the operator

Present the proposed breakdown as a numbered list. For each slice show:
- Title.
- Type (HITL or AFK).
- Blocked by (which slices must finish first).
- User stories covered (if the source PRD has them).

Ask:
- Does the granularity feel right?
- Are the dependency relationships correct?
- Should any slices be merged or split further?
- Are HITL and AFK marks correct?

Iterate until the operator approves.

### 5. Publish

For each approved slice, publish a new issue to the configured tracker in dependency order so blocking issue IDs are real by the time they are referenced.

Issue body template:

```
## Parent
<reference to parent issue, or omit>

## What to build
Concise description of the vertical slice. End-to-end behavior, not layer-by-layer implementation.

## Acceptance criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Blocked by
- <reference to blocker, or "None - can start immediately">
```

Do not close or modify any parent issue.

## Discipline

- Do not invent acceptance criteria the operator has not agreed to.
- Do not embed file paths or code snippets in issue bodies; they go stale fast.
- If issue tracker access is not available in this session, produce the breakdown as a markdown artifact and tell the operator where to publish it.
