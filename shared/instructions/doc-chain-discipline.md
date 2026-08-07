# Doc-Chain Discipline

When a repo uses `AGENTS.md`, `agents.md`, or equivalent local contract files, treat them as the navigation map for the work.

## Before editing

- Read the root contract file first.
- Identify the files or folders you expect to touch.
- Walk from repo root to each target path and read every applicable contract file on that route.
- If a parent doc points to a child doc index, follow that path before editing.
- Re-read the applicable doc chain in the current session instead of relying on memory.

## While editing

- Use parent docs for repo-wide rules and the closest doc for local rules.
- Keep the change inside the documented ownership boundary unless the task explicitly requires a wider change.
- Prefer the smallest edit that satisfies both the request and the local contract.

## After editing

- Do a doc pass before calling the task done.
- Update the nearest owning doc when the change affects structure, ownership, workflow, contracts, verification, or durable behavior.
- Update parent or child docs when their indexes or inherited rules changed.
- Remove stale or contradictory guidance immediately.

## Default posture

If a repo does not yet have a doc chain, use the normal onboarding flow. If it does, let the doc chain drive where you read, edit, and verify.

## Provenance

- Source: local Claude-OC-System default backbone doctrine plus internal Hermes-operator adaptation.
- Disposition: distilled-into-default.
- Notes: migrated as lean shared instruction text so Claude Code and Codex can inherit the same default intent.
