# Handoff

Compact the current conversation into a handoff doc so another agent or runtime can continue. Distilled from Matt Pocock's `handoff` skill. Complements `/save-session` (Hermes durable session capture) by producing a lightweight one-shot brief.

## When to invoke

- Operator says "handoff", "hand this off", "pass this to another agent".
- Session is approaching the compact band and the operator wants a clean break instead of compaction.
- A different runtime (Claude <-> Codex) is taking over mid-task.

## Where it goes

Write to the OS temp directory, not the working tree. Resolve via `$TMPDIR`, falling back to `/tmp` on Linux/macOS or `%TEMP%` on Windows. File name: `hermes-handoff-<short-task-name>-<timestamp>.md`. Tell the operator the absolute path.

## Required sections

1. **Mission** — one-sentence statement of what the next session must accomplish.
2. **Context links** — paths or URLs to existing artifacts (PRDs, plans, ADRs, issues, diffs). Reference, do not duplicate.
3. **State** — what the current session has already done, in 3-7 bullets.
4. **Open questions** — anything the operator has not yet decided.
5. **Suggested next moves** — the first 1-3 actions the next agent should take.
6. **Suggested loadout / skills** — recommended Hermes loadout and skills the next agent should invoke.

## Redaction

Before writing, strip:
- API keys, tokens, passwords
- personal identifiers
- internal hostnames or IPs that are not already in the public repo

## Anti-patterns

- Duplicating content from referenced artifacts.
- Inventing decisions the operator has not made.
- Writing into the repo working tree instead of the temp dir.
- Skipping the "suggested loadout / skills" section — that is the Hermes-specific value of this skill.

## Provenance

- Source: https://github.com/mattpocock/skills, classified in internal maintainer ingestion notes (2026-05-28, not shipped publicly).
- Disposition: distilled-into-default.
- Notes: adapted into the Hermes default backbone as a small, runtime-portable shared skill.
