# frontend-design loadout sources

This file accounts for the direct source surface named by this loadout manifest. It is intentionally local to the loadout so reviewers can inspect provenance from this file alone.

## Loadout manifest

- Manifest: `loadouts/frontend-design/loadout.yaml`
- Base: `default`
- Supported runtimes: `claude, codex`

This page lists direct entries on `frontend-design`. Inherited entries come from `loadouts/default/SOURCES.md`.

## Direct shared skills

- `verification-loop` — internal/legacy repo design
- `frontend-motion-audit` — internal/legacy repo design
- `shadcn-discipline` — internal/legacy repo design
- `impeccable-design-quality` — pbakaus/impeccable
- `minimalist-ui` — Leonxlnx/taste-skill

## Direct shared instructions

- `core-operating-rules` — internal/legacy repo design
- `context-discipline` — internal/legacy repo design
- `reporting-contract` — internal/legacy repo design
- `browser-verification` — internal/legacy repo design

## Direct packs

- `frontend-design` — internal loadout pack; inspect `shared/packs/frontend-design/PACK.md`.

## External sources used directly

| Source | Revision/license | Direct items | Evidence |
|---|---|---|---|
| `Leonxlnx/taste-skill` | b17742737e796305d829b3ad39eda3add0d79060; upstream license recorded in source audit | `minimalist-ui` | attribution recorded in this SOURCES.md |
| `pbakaus/impeccable` | 0d1c34e9d0fcfff1070c7210cd808eda504105d7; upstream license recorded in source audit | `impeccable-design-quality` | attribution recorded in this SOURCES.md |

## Internal/legacy entries

- `verification-loop` — Internal Hermes repo design or legacy Claude OpenClaw/OpenClaw-derived behavior; no external repo adoption recorded for this item.
- `frontend-motion-audit` — Internal Hermes repo design or legacy Claude OpenClaw/OpenClaw-derived behavior; no external repo adoption recorded for this item.
- `shadcn-discipline` — Internal Hermes repo design or legacy Claude OpenClaw/OpenClaw-derived behavior; no external repo adoption recorded for this item.
- `core-operating-rules` — Internal Hermes repo design or legacy Claude OpenClaw/OpenClaw-derived behavior; no external repo adoption recorded for this item.
- `context-discipline` — Internal Hermes repo design or legacy Claude OpenClaw/OpenClaw-derived behavior; no external repo adoption recorded for this item.
- `reporting-contract` — Internal Hermes repo design or legacy Claude OpenClaw/OpenClaw-derived behavior; no external repo adoption recorded for this item.
- `browser-verification` — Internal Hermes repo design or legacy Claude OpenClaw/OpenClaw-derived behavior; no external repo adoption recorded for this item.

## Referenced but not adopted as direct runtime material

These repos appear in the broader source-accounting system but are not direct materialized sources for this loadout unless listed above:

- `ruvnet/ruflo` — source-accounting only; no runtime materialization in current public surface. Development evidence stays in the maintainer source registry (development workspace, not shipped publicly).
- `affaan-m/ECC` — source-accounting only; no runtime materialization in current public surface. Development evidence stays in the maintainer source registry (development workspace, not shipped publicly).
- `obra/superpowers` — source-accounting only in v1.0; deferred architectural reference, not a current live-loadout source. Development evidence stays in the maintainer source registry (development workspace, not shipped publicly).
- maintainer intake queue — development-workspace reference list, not runtime-materialized, not shipped publicly.

## Update rule

When this loadout adds, removes, or rewires `shared_skills`, `shared_instructions`, or `packs`, update this file in the same commit. If a new external repo contributes material, record its adopted-source attribution in this SOURCES.md in the same commit; the maintainer source registry (not shipped publicly) tracks it separately.
