# Source Ingestion Step 3: Integration Plan

Turn the functionality-comparison ledger into a reviewable integration plan for an isolated prepare bundle.

## When to invoke

- Steps 1 and 2 are complete enough to decide what, if anything, should be prepared.
- The operator asks for the next concrete plan after analysis.
- `workflow.state_summary` shows steps 1-2 done and step 3 pending.

## Pipeline

1. Run the prepare stage into an isolated output root. (The adopt-source automation lives in the maintainer development workspace and does not ship with the public repo; follow the steps manually or with your own tooling.)

2. Read `workflow.steps[2]`, `staging_bundle`, `next_review_actions`, `candidate_suggestions`, and `analysis_readiness`.
3. Confirm the prepare bundle contains `PROPOSED-CHANGE.md`, `content-packet.json`, `staging-manifest.json`, `REVIEW.md`, and previews/stubs as applicable.
4. Confirm no canonical loadout/runtime file was live-written.
5. Record whether the plan is empty, blocked by unread bodies, or ready for packet authoring.

## Structured output

Emit or persist this compact step log:

```json
{
  "step": 3,
  "name": "integration plan",
  "source": "owner/repo",
  "status": "done|pending|blocked",
  "evidence": {
    "bundle_root": "/tmp/<review-root>",
    "proposed_change": "/tmp/<review-root>/PROPOSED-CHANGE.md",
    "review_doc": "/tmp/<review-root>/REVIEW.md",
    "candidate_count": 0
  },
  "next_step": 4,
  "next_command": "Review and author the generated content packet before apply."
}
```

## Discipline

Prepare is a planning/review action. It may create unapproved stubs in the isolated output root, but it must not claim anything is integrated or applyable until a reviewer authors exact content and approvals.