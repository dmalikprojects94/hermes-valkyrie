# Loadout Builder

Promptable admission test for a candidate capability against the Hermes default backbone. Cheap to run, deterministic in shape, judgment-driven in content.

## When to invoke

- Operator proposes adding a new instruction, skill, agent, command, hook, or MCP server to `default`.
- Operator asks whether an existing surface should be promoted from a specialty loadout into `default`.
- Operator asks whether something should leave `default` and move to a specialty.
- Operator provides a promising GitHub repo, Claude Code pack, Codex pack, or prompt/skill repo and asks to integrate it into the loadout system.

## Input

- **Candidate** — one line describing the capability.
- **Surface(s)** — which artifact type(s): instruction file, skill, agent, command, hook, MCP server.
- **Source** — required for external material: GitHub URL, upstream path, revision/date, and license if known; use your ingestion-report template for full repo passes.

## Pipeline

1. **Restate.** Re-express the candidate in one sentence. Refuse if ambiguous.
2. **Admission tests.** For each test, answer `pass` / `fail` / `unclear` with one supporting line:
   - Broadly useful across most work modes?
   - Low context cost when present in every default session?
   - Low ceremony (no specialty setup)?
   - Appropriate as inherited backbone for downstream loadouts?
3. **Coverage check.** Cross-reference the backbone capability map (Prompt shaping, Planning, Execution, Verification, Code review, Debugging, Research, Context discipline, Handoff, Performance analysis, Repo onboarding, Safety guardrails). If already covered, mark `duplicate` and stop unless the new surface materially strengthens an existing one.
4. **Specialty fit.** If admission fails, name the best-fit specialty loadout from the active set (`deep-coding`, `coding`, `project-planner`, `frontend-design`, `frontend-research-audit`, `open-design`, `research`, `media-video`).
5. **Verdict.** Exactly one of:
   - `keep-in-default` — admission passes, no duplicate.
   - `strengthen-existing` — duplicate, but worth merging into the existing default surface.
   - `route-to-specialty <name>` — admission fails, route elsewhere.
   - `reject` — fails admission and has no specialty fit.
6. **Wiring plan.** Only when verdict is `keep-in-default` or `strengthen-existing`. List the files to touch by category: instruction / skill / agent / command / hook / MCP / adapter registry / docs.
7. **Provenance plan.** For external material, name the source report path, the source-matrix ledger update, and any frame files that need `## Provenance` sections.
8. **Runtime sync plan.** Mark Claude/Codex parity as `synced`, `shared-only`, `acceptable-gap`, or `missing-*` per the loadout synchronization contract.

## Output shape

An 8-section report:

1. **Candidate** — restated in one sentence.
2. **Admission** — four lines, one per test.
3. **Coverage** — covered or new, with reference.
4. **Specialty fit** — named loadout or `n/a`.
5. **Verdict** — one of the four labels above.
6. **Wiring plan** — file list, or `n/a` if not applicable.
7. **Provenance plan** — source report, source matrix update, and frame-file provenance requirements.
8. **Runtime sync plan** — Claude/Codex parity category and any gaps.

## Discipline

- This is a judgment loop, not a deterministic gate. Output the report; do not auto-apply changes.
- Default-bias: when in doubt, route to specialty, not default. The cost of bloating default is paid in every session.
- Reuse beats new. If a candidate restates something already in default, mark it duplicate.
