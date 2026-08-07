# Code Review

Code review is backbone, not a specialty. Every non-trivial change passes through it.

## When to review

- Before declaring a multi-file change complete.
- When the diff touches shared infrastructure, security-sensitive paths, or external interfaces.
- When invoked explicitly via `/code-review` or `/review-pr`.

## Blast-radius severity

Rank each finding by how much breaks if it ships.

- **Critical** — data loss, security hole, broken auth, irreversible destructive op, production crash path.
- **High** — broken contract, silently incorrect output, regression in a covered behavior, breaking change to an external surface.
- **Medium** — degraded UX, partial coverage gaps, error handling that masks signal.
- **Low** — naming, structure, comment quality, style nits.

Critical and High block merge. Medium and Low are addressable but not gating.

## Breaking-change checks

- Did any public function, exported type, CLI flag, env var, or schema change shape?
- Did any default change?
- Is the migration path documented for callers?

If yes to any of these, surface the change explicitly in the review and confirm intent.

## Review checklist

- Diff scope matches the stated request — no smuggled refactors.
- New code matches existing patterns in the surrounding files.
- Error paths are sensible, not just present.
- Tests cover the behavior change, not just the lines.
- No dead code, debug prints, or commented-out blocks.
- No newly added secrets, credentials, or PII paths.

## Output shape

- Lead with Critical and High findings.
- Group remaining findings by file:line.
- For each finding: state the issue, then the suggested fix (one sentence each).
- End with an explicit verdict: `approve`, `approve-with-fixes`, `request-changes`.

## Provenance

- Source: local Claude-OC-System default backbone doctrine plus internal Hermes-operator adaptation.
- Disposition: distilled-into-default.
- Notes: migrated as lean shared instruction text so Claude Code and Codex can inherit the same default intent.
