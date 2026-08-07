# Source Ingestion Step 6: Closeout

Close the source-ingestion loop with accounting, git/CI evidence, and a resumable structured log.

## When to invoke

- Step 5 has applied and verified approved changes, or the pipeline intentionally stops at a blocked/refused safety result.
- The operator asks what changed, what remains, and how to continue.
- A later agent needs to resume from the last safe pipeline state.

## Pipeline

1. For approved implementations, confirm source accounting and per-loadout changelog entries were updated in the same commit.
2. Run final gates:

```bash
python scripts/validate_loadouts.py
python scripts/smoke_clean_hermes_onboarding.py --json
git diff --check
```

Capability-matrix regeneration checks are maintainer-workspace tooling and do not ship publicly; skip them on a public checkout.

3. Commit and push only durable source/docs/tests/loadout changes, never sandbox or raw runtime artifacts.
4. Watch GitHub Actions for the pushed commit.
5. Persist a compact structured run log with per-step statuses, evidence paths, next command, and any remaining blockers.

## Structured output

Emit or persist this compact step log:

```json
{
  "step": 6,
  "name": "closeout",
  "source": "owner/repo",
  "status": "done|blocked|rolled_back|pending",
  "evidence": {
    "commit": "sha-or-null",
    "ci_run": "url-or-null",
    "verification": {},
    "structured_log": "docs/verification/...json"
  },
  "next_step": null,
  "next_command": "None, or the exact resume command for the next unresolved step."
}
```

## Discipline

Closeout is evidence, not vibes. If the run stops because the packet is unapproved or analysis is incomplete, report that state directly and preserve the exact next command instead of calling the source integrated.