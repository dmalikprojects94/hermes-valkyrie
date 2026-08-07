# Source Ingestion Step 5: Implementation + Validation

Apply only an approved, attributed packet and verify that the implementation actually works.

## When to invoke

- Step 4 produced an approved proposed-change packet.
- The operator wants to test the apply gate or implement approved source-derived changes.
- `workflow.next_command` points to the apply stage.

## Pipeline

1. Confirm the working tree is clean outside the approved allowlist.
2. Run the apply stage against the approved `PROPOSED-CHANGE.md` packet. (The adopt-source automation lives in the maintainer development workspace and does not ship with the public repo; follow the steps manually or with your own tooling.)

3. If the packet is unapproved, verify refusal: zero applied files, step 5 `blocked`, no live writes.
4. If the packet is approved, verify applied files, validators, capability matrix, tests, and rollback behavior on failure.
5. Preserve the apply report's `workflow.steps[4]` evidence.

## Structured output

Emit or persist this compact step log:

```json
{
  "step": 5,
  "name": "implementation + validation",
  "source": "owner/repo",
  "status": "done|blocked|rolled_back|pending",
  "evidence": {
    "applied_files": [],
    "verification": {},
    "refusal_reason": null,
    "rollback_performed": false
  },
  "next_step": 6,
  "next_command": "Record source accounting, commit, push, and watch CI when implementation is approved and verified."
}
```

## Discipline

A blocked/refused apply is a successful safety test, not a failed pipeline, when the packet is intentionally unapproved. A real implementation is done only after validators and tests pass against approved content.