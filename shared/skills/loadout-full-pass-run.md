# Loadout Full-Pass Run

Run the complete source-ingestion path through confirmation, isolated proof, and final new loadout build when approval is present. Full-pass never means skipping review; it means continuing only after confirmation gates pass.

## When to invoke

- The operator explicitly asks for a full pass run.
- A reviewed run has produced confirmation and the operator wants the system to continue.
- A confirmed builder/proposed-change packet is supplied.
- The goal is to end with a real new loadout build or approved existing-loadout patch.

## If/then routing

- IF Step 1 repo map/audit has not run, THEN invoke `source-ingestion-step-1-repo-map-audit`.
- IF Step 2 functionality comparison has not run, THEN invoke `source-ingestion-step-2-functionality-comparison`.
- IF prepare artifacts do not exist, THEN invoke `source-ingestion-step-3-integration-plan` and `source-ingestion-step-4-change-packet-review`.
- IF confirmation is missing, THEN fall back to the reviewed-run stop point and return `status: approval_gate`.
- IF any op lacks approved=true, reviewer, attribution, authored content, source/revision, or allowlisted path, THEN stop at `status: approval_gate`.
- IF confirmation is present, THEN run isolated builder/apply proof first.
- IF isolated proof fails, THEN stop with `status: blocked` and do not live-write.
- IF isolated proof passes and live build is explicitly allowed, THEN perform the new loadout build.
- IF validation fails after live build, THEN rollback or stop with clear blockers.

## Strict checklist

- [ ] Re-run or verify Step 1 repo map/audit evidence.
- [ ] Re-run or verify Step 2 comparison evidence.
- [ ] Produce/read prepare artifacts: candidate analysis, builder packet, approval checklist, proposed files.
- [ ] Confirm the approval artifact has approve/change/drop decisions.
- [ ] Confirm every approved op has reviewer, attribution, authored content, source/revision, and exact path allowlist.
- [ ] Confirm Claude/Codex parity or documented intentional gap.
- [ ] Run isolated apply/build proof under `/tmp` or supplied output root.
- [ ] Verify generated loadout YAML, docs, registry/projection files, and command inventory if commands changed.
- [ ] Only after isolated proof, perform the new loadout build or approved patch.
- [ ] Record the source accounting update in your maintainer notes when source-derived behavior lands.
- [ ] Update `docs/loadouts/<loadout>/CHANGELOG.md`.
- [ ] Refresh/check capability matrix.
- [ ] Run validators and tests.
- [ ] Commit, push, and verify CI when live repo changes are made.

## Concrete run shape

The pipeline and builder automation for this workflow lives in the maintainer development workspace and does not ship with the public repo; follow the steps manually or with your own tooling.

1. Produce the prepare/full-pass review bundle (surface analysis included) into an isolated output root.
2. Run the builder isolated proof from the confirmed packet into a proof-only output root.
3. Only after proof and confirmation, perform the live build, then validate:

```bash
python scripts/validate_loadouts.py
python scripts/smoke_clean_hermes_onboarding.py --json
```

## Output contract

```json
{
  "run_type": "full-pass",
  "status": "approval_gate|blocked|built",
  "confirmation_present": true,
  "isolated_proof": "passed|failed|not_run",
  "live_writes": false,
  "new_loadout_built": false,
  "materialized_files": [],
  "validation": {
    "validate_loadouts": "passed|failed|not_run",
    "capability_matrix": "fresh|stale|not_run",
    "tests": "passed|failed|not_run"
  },
  "commit": null,
  "ci": "success|failed|not_run"
}
```

## Final new loadout build definition

A new loadout build is complete only when these exist and validate as applicable:

- `loadouts/<name>/loadout.yaml`
- shared skills/instructions introduced for the loadout
- Claude command/agent/hook/MCP registry entries when needed
- Codex equivalent skills/command projections or documented intentional gap
- `docs/loadouts/<name>/CHANGELOG.md`
- loadout catalog/docs update
- source accounting update
- refreshed capability matrix
- validation/test output
- committed and pushed repo state with CI success

## Boundary

Full-pass does not bypass review. If confirmation is absent or incomplete, full-pass must stop exactly where reviewed run stops, report the missing confirmation fields, and build nothing live.
