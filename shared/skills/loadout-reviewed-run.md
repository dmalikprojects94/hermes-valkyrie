# Loadout Reviewed Run

Run the safe review-only source-ingestion path. This run analyzes the repo, determines what belongs in the loadout prepare step, produces a confirmation artifact, and stops.

## When to invoke

- The operator asks for a reviewed run.
- The operator wants to see what would enter loadout prepare before allowing a full pass.
- The source is new, risky, large, or unconfirmed.
- The orchestrator defaults an ambiguous request to safety.

## If/then routing

- IF Step 1 repo map/audit has not run, THEN invoke `source-ingestion-step-1-repo-map-audit`.
- IF Step 2 functionality comparison has not run, THEN invoke `source-ingestion-step-2-functionality-comparison`.
- IF Step 1 or Step 2 is blocked, THEN stop with `status: blocked`.
- IF candidate rows exist, THEN produce the prepare-selection confirmation artifact.
- IF no trusted-ready rows exist, THEN report why and stop with `status: review_pending` or `no_candidates`.
- IF confirmation is requested, THEN ask for approve/change/drop decisions in the confirmation artifact only; do not continue.
- IF any instruction implies live apply, THEN refuse within reviewed run and point to full-pass after confirmation.
- STOP after prepare-selection confirmation.

## Strict checklist

- [ ] Run/read Step 1 repo map/audit evidence.
- [ ] Run/read Step 2 comparison against the loadout capability matrix.
- [ ] Identify exactly which rows would enter prepare.
- [ ] Split candidates into trusted-ready, needs body/function review, adapter-deferred, reference-only, duplicate/already-covered, and unsafe/drop.
- [ ] Produce a confirmation artifact with approve/change/drop rows.
- [ ] Include exact source/revision, evidence path, target loadout/path, and missing fields per row.
- [ ] Set `live_writes: false`.
- [ ] Set `apply_attempted: false`.
- [ ] Set `new_loadout_built: false`.
- [ ] Do not run loadout-builder apply.
- [ ] Do not create or patch live loadout files.

## Concrete run shape

The repo-pipeline automation for this workflow lives in the maintainer development workspace and does not ship with the public repo; follow the steps manually or with your own tooling.

Prefer the reviewed/audit path when available: run the audit-mode pass with surface analysis. If the operator wants the review bundle/staging artifacts but still no apply, run the full-pass mode into an isolated output root.

This is still reviewed behavior unless a confirmed packet is supplied and the full-pass skill owns the continuation.

## Output contract

```json
{
  "run_type": "reviewed",
  "status": "review_pending|no_candidates|blocked",
  "steps_complete": [1, 2],
  "prepare_selection": {
    "trusted_ready": [],
    "needs_review": [],
    "adapter_deferred": [],
    "reference_only": [],
    "drop": []
  },
  "confirmation_required": true,
  "apply_attempted": false,
  "live_writes": false,
  "new_loadout_built": false,
  "next_step": "run the full-pass pipeline for <owner/repo> into an isolated output root"
}
```

## Confirmation artifact template

```text
Source/revision reviewed:
Rows approved for prepare:
Rows changed before prepare:
Rows dropped/deferred:
Required target loadout/path per approved row:
Missing fields before full pass:
Reviewer:
Approval statement:
```

## Boundary

Reviewed run means review-only. It ends at prepare-selection confirmation, not at builder apply and not at live loadout build.
