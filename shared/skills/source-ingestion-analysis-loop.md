# Source Ingestion Analysis Loop

Deeply inventory one GitHub source repo at a pinned revision, compare it against the
committed loadout capability matrix, and emit a **capability-gap decision ledger** the
upgrade loop can consume. This is the named analysis half of the two-loop ingestion
surface. It never writes live loadout files and never applies anything.

This skill is the operator entrypoint. It orchestrates the existing mechanics
(`source-ingestion-step-1-repo-map-audit`, `source-ingestion-step-2-functionality-comparison`,
and the `adopt-source --stage injection-prep` CLI) — do not re-derive their internals here.

## When to use

- The operator wants to know what a GitHub repo could add to the loadout system, with exact placement verdicts, before any change is authored.
- You are handed `owner/repo` (optionally a pinned revision) and asked to "analyze", "audit for ingestion", or "check what we should adopt".
- The next human action should be reviewing a decision ledger, not being asked to prepare one.

## Inputs

- `source`: `owner/repo` (required).
- `revision`: pinned commit/tag; if absent, pin the current default-branch HEAD and record it.
- `output_root`: isolated artifact directory (e.g. `/tmp/<repo>-analysis`). Never the repo tree.

## Loop

1. **Pin.** Start from a clean local tree; record the baseline commit. Resolve and record the exact upstream revision (SHA). All claims are anchored to that SHA.
2. **Inventory.** Enumerate every meaningful upstream surface as an evaluable row: skills, commands, agents, hooks, adapters, MCP/tool surfaces, docs/reference files, tests/fixtures, installer/runtime packaging, generated outputs, browser/runtime extensions. Use `repo-surface-auditor` discipline.
3. **Classify each row.** Distinguish canonical source files from: reference docs, generated outputs, fixtures, command-map prompt tokens, invocation commands, and adapter-only surfaces. A path that is only referenced is not the behavior.
4. **Read bodies.** Before claiming any behavior extraction, read the actual file body. No behavior claim is allowed from a filename or a directory listing alone. Record the evidence path per claim.
5. **Compare.** Diff upstream capabilities against the generated loadout capability matrix and the existing loadout inventory under `loadouts/`. For each capability decide whether the system already covers it.
6. **Decide.** Assign every row exactly one placement verdict (see vocabulary). Name the exact proposed target file/loadout/adapter and say why.
7. **Emit.** Produce the injection-prep bundle so the ledger is both human-readable and machine-consumable. (The injection-prep automation lives in the maintainer development workspace and does not ship with the public repo; produce the bundle manually or with your own tooling.)

That bundle carries `INJECTION-PREP.md` (human), `injection-prep.json` (machine, one item per surface row with disposition + evidence + verification + rollback), and `injection-decisions.template.json` (the reviewer response form). Confirm `live_writes: false` and the working tree is unchanged.

## Decision verdict vocabulary

Every surface row gets exactly one:

- `add shared skill` — new distilled skill under `shared/skills/`.
- `patch existing skill` — extend a named existing skill.
- `adapter-needed` — hook/CLI/browser/runtime behavior requiring a separate adapter path + reversible canary. Never a blind import.
- `process-only` — a workflow/doctrine change, no runtime surface.
- `repo-resident-reference` — keep as reference doc, not a runtime surface.
- `already-covered` — the system already does this; cite the covering surface.
- `defer` — real but not now; record the trigger to revisit.
- `drop` — not worth adopting; record why.

## Structured output

Emit this compact loop log alongside the bundle:

```json
{
  "loop": "source-ingestion-analysis-loop",
  "source": "owner/repo",
  "revision": "<sha>",
  "output_root": "<isolated>",
  "surfaces_total": 0,
  "verdict_counts": {"add shared skill": 0, "patch existing skill": 0, "adapter-needed": 0, "process-only": 0, "repo-resident-reference": 0, "already-covered": 0, "defer": 0, "drop": 0},
  "body_read_evidence": true,
  "bundle": {"markdown": "<path>", "json": "<path>", "decisions_template": "<path>"},
  "live_writes": false,
  "next_loop": "source-ingestion-upgrade-loop",
  "next_command": "fill injection-decisions.template.json, then run the upgrade loop"
}
```

## Discipline

- Analysis is read-only. If any live write is observed during this loop, stop and report a safety violation.
- No behavior claim without a body-read evidence path.
- Do not hand the operator a candidate-only or path-only list as if it were a decision ledger. Every row carries a verdict and a named target.
- This loop stops at the decision ledger. It does not author content or apply — that is the upgrade loop.

## Provenance

- Source: internal Hermes-operator runtime-surface design; consolidates the reviewed-ingestion Step 1–2 mechanics into a named operator loop.
- Disposition: distilled-into-loadout (loadout-management).
- Notes: named analysis surface requested after the pbakaus/impeccable ingestion showed the middle of the pipeline was not yet a repeatable Claude Code loop.
