# Two-Axis Review

Review a change along two independent axes — Standards (does the code follow this repo's documented conventions?) and Spec (does the code match what the originating request asked for?). Distilled from Matt Pocock's `review` skill. Complements the existing `/code-review` and `/review-pr` commands by adding a deliberate axis split.

## When to invoke

- Operator says "review this branch", "two-axis review", "did we build the right thing".
- A change is about to merge and the operator wants both correctness and conformance signal.
- A PR has been flagged for closer inspection.

## Process

### 1. Pin the fixed point

Whatever the operator gave is the fixed point — a commit SHA, branch name, tag, `main`, `HEAD~5`. Do not be opinionated. If the operator did not specify one, ask: "Review against what — a branch, a commit, or `main`?" Do not proceed without it.

Capture the diff once: `git diff <fixed-point>...HEAD` (three-dot, so the comparison is against the merge base). Note the commit list via `git log <fixed-point>..HEAD --oneline`.

### 2. Identify the spec source

Look in this order:
1. Issue or PR references in commit messages.
2. A path the operator passed as an argument.
3. A PRD, plan, or spec file under `docs/`, `specs/`, or `.scratch/` matching the branch name or feature.
4. If nothing is found, ask. If the operator says there is no spec, the Spec axis reports "no spec available" instead of being skipped silently.

### 3. Identify the standards sources

Anything in the repo that documents how code should be written:
- `CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`.
- Per-repo `CONTEXT.md` or shared instruction files.
- `docs/adr/` — architectural decisions are standards.
- Style or lint config files. Note them but do not re-check what tooling already enforces.

### 4. Run the axes

The two axes are independent and must not pollute each other.

**Standards axis** — read the standards docs, then the diff. Report every place the diff violates a documented standard. Cite the standard (file + rule). Distinguish hard violations from judgement calls. Skip what tooling already enforces.

**Spec axis** — read the spec, then the diff. Report (a) requirements the spec asked for that are missing or partial, (b) behavior in the diff that was not asked for (scope creep), (c) requirements that look implemented but where the implementation looks wrong. Quote the spec line for each finding.

When delegating these axes to sub-agents, run them in parallel so neither sees the other's context.

### 5. Aggregate

Present the two reports under `## Standards` and `## Spec` headings. Do not merge findings. End with a one-line summary: total findings per axis, and the worst single issue.

## Why two axes

A change can pass one axis and fail the other:
- Code that follows every standard but implements the wrong thing -> Standards pass, Spec fail.
- Code that does exactly what was asked but breaks the project's conventions -> Spec pass, Standards fail.

Reporting them separately stops one axis from masking the other.

## Discipline

- Two-axis review is in addition to, not a replacement for, blast-radius severity and breaking-change checks from `code-review` instruction.
- If the spec is missing, do not invent one. Report "no spec available" and move on.
- Verdict is per-axis, not a single combined verdict.
