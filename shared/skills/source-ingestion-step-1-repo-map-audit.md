# Source Ingestion Step 1: Injection Preparation

Produce the complete no-live-write injection-prep bundle for the reviewed source-ingestion pipeline.

## When to invoke

- The operator asks to start testing, reviewing, or adopting a GitHub source repo.
- The next human action should be reviewing the proposed injection, not asking the system to prepare it.
- A later agent needs a concrete bundle that says exactly what would be injected, where, why, and with what approval/verification/rollback requirements.

## Pipeline

1. Start from a clean local tree and record the baseline commit.
2. Run or implement the reviewed ingestion first-stage path: an injection-prep pass with surface analysis into an isolated output root. (The pipeline automation for this lives in the maintainer development workspace and does not ship with the public repo; follow the steps manually or with your own tooling.)

A bare audit/comparison pass is only an internal component; it is not the completed Step 1 product.

3. The Step 1 product must include `INJECTION-PREP.md` or `injection-prep-*.md`, a matching JSON artifact, `PROPOSED-CHANGE.md`, `content-packet.json`, `staging-manifest.json`, proposed/authoring-required content paths, and accounting/changelog/capability/verification/rollback previews.
4. Confirm it writes only under the isolated output root, leaves all ops `approved:false`, and does not touch live loadout files.

## Structured output

Emit or persist this compact step log:

```json
{
  "step": 1,
  "name": "injection preparation",
  "source": "owner/repo",
  "status": "done|pending|blocked",
  "evidence": {
    "injection_prep_markdown": "path-or-null",
    "injection_prep_json": "path-or-null",
    "proposed_change": "path-or-null",
    "content_packet": "path-or-null",
    "staging_manifest": "path-or-null",
    "ready_for_review_ops": 0,
    "not_ready_rows": 0,
    "live_writes": false,
    "approved_ops": 0
  },
  "next_step": 2,
  "next_command": "review the injection-prep bundle; do not run apply until review approves exact ops"
}
```

## Discipline

Step 1 answers: what exact injection is ready for review? It includes repo audit and comparison internally, but it must not stop at those. Do not ask the operator to review a candidate-only or path-only ledger as if it were an injection proposal.
