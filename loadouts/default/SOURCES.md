# default loadout sources

This file accounts for the direct source surface named by this loadout manifest. It is intentionally local to the loadout so reviewers can inspect provenance from this file alone.

## Loadout manifest

- Manifest: `loadouts/default/loadout.yaml`
- Base: none
- Supported runtimes: `claude, codex`

## Direct shared skills

- `verification-loop` — internal/legacy repo design
- `prompt-optimizer` — internal/legacy repo design
- `ponytail` — DietrichGebert/ponytail
- `ponytail-review` — DietrichGebert/ponytail
- `ponytail-audit` — DietrichGebert/ponytail
- `ponytail-debt` — DietrichGebert/ponytail
- `ponytail-help` — DietrichGebert/ponytail
- `careful` — internal/legacy repo design
- `research-ops` — internal/legacy repo design
- `repo-onboarding` — internal/legacy repo design
- `caveman` — mattpocock/skills, DietrichGebert/ponytail
- `zoom-out` — mattpocock/skills
- `handoff` — mattpocock/skills
- `obsidian-output-routing` — internal/legacy repo design
- `hermes-update-readiness` — internal/legacy repo design
- `devops-ops` — internal/legacy repo design

## Direct shared instructions

- `core-operating-rules` — internal/legacy repo design
- `prompt-discipline` — internal/legacy repo design
- `context-discipline` — internal/legacy repo design
- `doc-chain-discipline` — internal/legacy repo design
- `delegation-policy` — internal/legacy repo design
- `planning-posture` — internal/legacy repo design
- `ponytail-default` — DietrichGebert/ponytail
- `coding-discipline` — internal/legacy repo design
- `development-workflow` — internal/legacy repo design
- `testing-baseline` — internal/legacy repo design
- `code-review` — internal/legacy repo design
- `security-baseline` — internal/legacy repo design
- `git-workflow` — internal/legacy repo design
- `reporting-contract` — internal/legacy repo design

## Direct packs

- None.

## External sources used directly

| Source | Revision/license | Direct items | Evidence |
|---|---|---|---|
| `DietrichGebert/ponytail` | 0cdd11fe0c56c3cda3380276ac271b255eea296a for follow-on; helper skill files also record earlier 795ec0ee3678d2fd92f7d118396855e9dcd591dc provenance; MIT | `caveman`, `ponytail`, `ponytail-audit`, `ponytail-debt`, `ponytail-default`, `ponytail-help`, `ponytail-review` | attribution recorded in this SOURCES.md |
| `mattpocock/skills` | not recorded in the original 2026-05-28 report; upstream repo; exact license not recorded in current baseline report | `caveman`, `handoff`, `zoom-out` | attribution recorded in this SOURCES.md |

## Internal/legacy entries

- `verification-loop` — Internal Hermes repo design or legacy Claude OpenClaw/OpenClaw-derived behavior; no external repo adoption recorded for this item.
- `prompt-optimizer` — Internal Hermes repo design or legacy Claude OpenClaw/OpenClaw-derived behavior; no external repo adoption recorded for this item.
- `careful` — Internal Hermes repo design or legacy Claude OpenClaw/OpenClaw-derived behavior; no external repo adoption recorded for this item.
- `research-ops` — Internal Hermes repo design or legacy Claude OpenClaw/OpenClaw-derived behavior; no external repo adoption recorded for this item.
- `repo-onboarding` — Internal Hermes repo design or legacy Claude OpenClaw/OpenClaw-derived behavior; no external repo adoption recorded for this item.
- `obsidian-output-routing` — Internal Hermes repo design or legacy Claude OpenClaw/OpenClaw-derived behavior; no external repo adoption recorded for this item.
- `hermes-update-readiness` — Internal Hermes repo design or legacy Claude OpenClaw/OpenClaw-derived behavior; no external repo adoption recorded for this item.
- `devops-ops` — Internal Hermes repo design or legacy Claude OpenClaw/OpenClaw-derived behavior; no external repo adoption recorded for this item.
- `core-operating-rules` — Internal Hermes repo design or legacy Claude OpenClaw/OpenClaw-derived behavior; no external repo adoption recorded for this item.
- `prompt-discipline` — Internal Hermes repo design or legacy Claude OpenClaw/OpenClaw-derived behavior; no external repo adoption recorded for this item.
- `context-discipline` — Internal Hermes repo design or legacy Claude OpenClaw/OpenClaw-derived behavior; no external repo adoption recorded for this item.
- `doc-chain-discipline` — Internal Hermes repo design or legacy Claude OpenClaw/OpenClaw-derived behavior; no external repo adoption recorded for this item.
- `delegation-policy` — Internal Hermes repo design or legacy Claude OpenClaw/OpenClaw-derived behavior; no external repo adoption recorded for this item.
- `planning-posture` — Internal Hermes repo design or legacy Claude OpenClaw/OpenClaw-derived behavior; no external repo adoption recorded for this item.
- `coding-discipline` — Internal Hermes repo design or legacy Claude OpenClaw/OpenClaw-derived behavior; no external repo adoption recorded for this item.
- `development-workflow` — Internal Hermes repo design or legacy Claude OpenClaw/OpenClaw-derived behavior; no external repo adoption recorded for this item.
- `testing-baseline` — Internal Hermes repo design or legacy Claude OpenClaw/OpenClaw-derived behavior; no external repo adoption recorded for this item.
- `code-review` — Internal Hermes repo design or legacy Claude OpenClaw/OpenClaw-derived behavior; no external repo adoption recorded for this item.
- `security-baseline` — Internal Hermes repo design or legacy Claude OpenClaw/OpenClaw-derived behavior; no external repo adoption recorded for this item.
- `git-workflow` — Internal Hermes repo design or legacy Claude OpenClaw/OpenClaw-derived behavior; no external repo adoption recorded for this item.
- `reporting-contract` — Internal Hermes repo design or legacy Claude OpenClaw/OpenClaw-derived behavior; no external repo adoption recorded for this item.

## Referenced but not adopted as direct runtime material

These repos appear in the broader source-accounting system but are not direct materialized sources for this loadout unless listed above:

- `ruvnet/ruflo` — source-accounting only; no runtime materialization in current public surface. Development evidence stays in the maintainer source registry (development workspace, not shipped publicly).
- `affaan-m/ECC` — source-accounting only; no runtime materialization in current public surface. Development evidence stays in the maintainer source registry (development workspace, not shipped publicly).
- `obra/superpowers` — source-accounting only in v1.0; deferred architectural reference, not a current live-loadout source. Development evidence stays in the maintainer source registry (development workspace, not shipped publicly).
- maintainer intake queue — development-workspace reference list, not runtime-materialized, not shipped publicly.

## Update rule

When this loadout adds, removes, or rewires `shared_skills`, `shared_instructions`, or `packs`, update this file in the same commit. If a new external repo contributes material, record its adopted-source attribution in this SOURCES.md in the same commit; the maintainer source registry (not shipped publicly) tracks it separately.
