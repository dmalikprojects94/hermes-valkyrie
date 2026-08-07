# marketing loadout sources

This file accounts for the direct source surface named by this loadout manifest. It is intentionally local to the loadout so reviewers can inspect provenance from this file alone.

## Loadout manifest

- Manifest: `loadouts/marketing/loadout.yaml`
- Base: `default`
- Supported runtimes: `claude, codex`

This page lists direct entries on `marketing`. Inherited entries come from `loadouts/default/SOURCES.md`.

## Direct shared skills

- `prompt-optimizer` — internal/legacy repo design
- `research-ops` — internal/legacy repo design
- `marketing-copy` — internal/legacy repo design

## Direct shared instructions

- `core-operating-rules` — internal/legacy repo design
- `prompt-discipline` — internal/legacy repo design
- `context-discipline` — internal/legacy repo design
- `reporting-contract` — internal/legacy repo design

## Direct packs

- `marketing` — internal loadout pack; inspect `shared/packs/marketing/PACK.md`.

## External sources used directly

No external adopted source is directly wired by this manifest. Its behavior is internal or inherited from its base loadout.

## Internal/legacy entries

- `prompt-optimizer` — Internal Hermes repo design or legacy Claude OpenClaw/OpenClaw-derived behavior; no external repo adoption recorded for this item.
- `research-ops` — Internal Hermes repo design or legacy Claude OpenClaw/OpenClaw-derived behavior; no external repo adoption recorded for this item.
- `marketing-copy` — Internal Hermes repo design or legacy Claude OpenClaw/OpenClaw-derived behavior; no external repo adoption recorded for this item.
- `core-operating-rules` — Internal Hermes repo design or legacy Claude OpenClaw/OpenClaw-derived behavior; no external repo adoption recorded for this item.
- `prompt-discipline` — Internal Hermes repo design or legacy Claude OpenClaw/OpenClaw-derived behavior; no external repo adoption recorded for this item.
- `context-discipline` — Internal Hermes repo design or legacy Claude OpenClaw/OpenClaw-derived behavior; no external repo adoption recorded for this item.
- `reporting-contract` — Internal Hermes repo design or legacy Claude OpenClaw/OpenClaw-derived behavior; no external repo adoption recorded for this item.

## Referenced but not adopted as direct runtime material

These repos appear in the broader source-accounting system but are not direct materialized sources for this loadout unless listed above:

- `ruvnet/ruflo` — source-accounting only; no runtime materialization in current public surface. Development evidence stays in the maintainer source registry (development workspace, not shipped publicly).
- `affaan-m/ECC` — source-accounting only; no runtime materialization in current public surface. Development evidence stays in the maintainer source registry (development workspace, not shipped publicly).
- `obra/superpowers` — source-accounting only in v1.0; deferred architectural reference, not a current live-loadout source. Development evidence stays in the maintainer source registry (development workspace, not shipped publicly).
- maintainer intake queue — development-workspace reference list, not runtime-materialized, not shipped publicly.

## Update rule

When this loadout adds, removes, or rewires `shared_skills`, `shared_instructions`, or `packs`, update this file in the same commit. If a new external repo contributes material, record its adopted-source attribution in this SOURCES.md in the same commit; the maintainer source registry (not shipped publicly) tracks it separately.
