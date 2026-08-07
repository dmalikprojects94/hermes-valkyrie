# Loadout Ingestion Orchestrator

Route a source-ingestion request into the correct run-type skill. Keep this skill thin: it decides run type, invokes the matching run skill, and enforces the stop/go contract.

## When to invoke

- The operator asks to ingest, review, full-pass, or build loadout capabilities from a GitHub repo/source pack.
- The request mentions reviewed run, full pass run, source ingestion, or loadout builder orchestration.
- The run type is ambiguous and must safely default to review.

## Inputs

- `source`: GitHub repo or source identifier, e.g. `owner/repo`.
- `run_type`: `reviewed` or `full-pass`; if missing, default to `reviewed`.
- `output_root`: isolated artifact directory for review/build output.
- `confirmation`: optional approved confirmation packet or approval state.

## If/then routing

- IF run_type is `reviewed`, THEN invoke `loadout-reviewed-run`.
- IF run_type is `full-pass`, THEN invoke `loadout-full-pass-run`.
- IF run_type is missing, unclear, or unsafe, THEN default to `reviewed`.
- IF the caller asks for full-pass but provides no confirmation, THEN still route to `loadout-full-pass-run`; that skill must fall back to the reviewed-run stop point.
- IF a lower-level step reports live writes during analysis/review, THEN stop and report a safety violation.

## Strict checklist

- [ ] Normalize the source identifier.
- [ ] Resolve run type: `reviewed` or `full-pass`.
- [ ] Confirm `output_root` is isolated for non-live stages.
- [ ] Load the selected run-type skill.
- [ ] Preserve the selected run type in every artifact and final summary.
- [ ] Report `live_writes`, `apply_attempted`, `confirmation_required`, and `new_loadout_built`.
- [ ] Never reinterpret reviewed output as approval.

## Output contract

Return a compact routing summary:

```json
{
  "orchestrator": "loadout-ingestion-orchestrator",
  "source": "owner/repo",
  "run_type": "reviewed|full-pass",
  "dispatched_skill": "loadout-reviewed-run|loadout-full-pass-run",
  "status": "review_pending|approval_gate|built|blocked",
  "live_writes": false,
  "new_loadout_built": false,
  "next_command": "..."
}
```

## Boundary

This skill does not analyze repos, author packets, approve content, or build loadouts. It only chooses and supervises the run-type workflow.
