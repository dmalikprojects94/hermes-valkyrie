# Documentation Purpose

This documentation exists to make the Terminal Loadout System understandable, runnable, extensible, and safe to operate as a public Hermes-adjacent project.

The project purpose is specific: **Hermes manages coding agents, and this repo gives Hermes a loadout system for managing context, skills, commands, hooks, and runtime-specific agent homes more efficiently for Claude Code and Codex.**

The docs should let a new human operator or AI coding agent do the full loop without private context:

1. Understand why loadouts exist and how they reduce always-on context bloat.
2. Install or clone the repo safely.
3. Validate the loadout definitions.
4. Resolve a request into a `(runtime, loadout)` pair.
5. Materialize a sandbox Claude Code or Codex runtime home.
6. Inspect the generated files and provenance manifest.
7. Choose when to write into a live runtime home.
8. Add or modify a loadout without breaking the default backbone.
9. Keep Claude Code and Codex behavior synchronized unless a runtime gap is intentional and documented.
10. Integrate with Hermes as the orchestrator while keeping the repo usable as a standalone loadout generator.

## Audience model

The docs serve two readers.

**Operators** need the human story: what the system does, which loadout to choose, how to run it safely, and how to avoid polluting live runtime homes.


**Maintainers** need architecture contracts, contribution rules, sanitization boundaries, and public-copy verification so the repo can evolve without reintroducing private control-plane assumptions.

## Documentation contract

Every public doc should help one of these outcomes:

- Explain the system model: Hermes chooses the runtime and loadout separately.
- Teach a runnable workflow: validate, resolve, materialize, inspect, then optionally launch.
- Define a safe extension path: add shared intent once, adapt it per runtime, verify both surfaces.
- Preserve trust boundaries: no private paths, identities, secrets, live-home artifacts, or operator-specific routing.
- Keep the public tree self-sufficient: every documented workflow must be runnable from this repo alone.

If a doc does not help one of those outcomes, it does not belong in this tree.

## Public-release rule (maintainer note)

The maintainer development workspace may contain historical plans, source-ingestion evidence, local runtime state, Hermes control-plane hooks, and operator-specific verification records. The public repo contains only the portable loadout system and the docs needed to run, extend, and verify it — and must stay usable exactly as shipped.
