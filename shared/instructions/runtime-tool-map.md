# Runtime Tool Map

## Purpose

Map shared Hermes loadout intent onto runtime-specific surfaces without duplicating behavior.

Preserve intent, not syntax.

Claude, Codex, and future runtimes can expose the same operational behavior through different mechanisms. The map records how each runtime represents skills, commands, hooks, agents, config, and delegated work.

## Mapping rules

1. Start with shared intent in `shared/instructions`, `shared/skills`, or `shared/packs`.
2. Add a Claude adapter only when Claude needs slash commands, agents, hooks, or MCP wiring.
3. Add a Codex adapter only when Codex needs config, memories, native slash-command documentation, or command-equivalent skills.
4. If parity is impossible, mark the exact gap. Do not invent fake equivalence.
5. If upstream behavior duplicates an existing Hermes skill, update the existing skill or reject the upstream item. Do not create redundant systems.

## Capability buckets

- `skill_bootstrap`: how the runtime discovers and presents active skills.
- `slash_commands`: native commands or command-equivalent skill triggers.
- `delegated_work`: subagents, task tools, parallel workers, or explicit fallback.
- `runtime_hooks`: SessionStart/Stop/tool hooks and their event names.
- `mcp`: model-context/tool servers exposed to the runtime.
- `memory`: durable or session-local memory surfaces.
- `safety`: sandbox, approval, and trust behavior.

## Adoption checklist

Before accepting behavior from a GitHub repo:

- record source repo, inspected revision, license, and evidence paths;
- decide whether behavior extends an existing loadout or proposes a new one;
- map Claude and Codex separately;
- reject redundant surfaces;
- generate a migration task pack before touching `loadouts/`, `shared/`, or `adapters/`.

## Provenance

- Source: internal maintainer source-recheck notes on Superpowers (2026-06-18, not shipped publicly)
- Evidence: Superpowers runtime plugin manifests and `docs/porting-to-a-new-harness.md`
- Disposition: distilled runtime parity map for Hermes adapters.
