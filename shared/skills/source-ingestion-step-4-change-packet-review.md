# Source Ingestion Step 4: Keep / Update / Remove Packet

Review, author, and approve the exact content packet that controls what may be applied.

## When to invoke

- Step 3 produced an isolated prepare bundle.
- The operator needs a concrete create/update/remove packet before implementation.
- `workflow.state_summary` shows step 4 as `review_pending`.

## Pipeline

1. Open the prepare bundle's `PROPOSED-CHANGE.md`, `content-packet.json`, `staging-manifest.json`, and `REVIEW.md`.
2. Separate no-op/accounting rows from real content operations.
3. For each operation that should move forward, author exact non-fixture content and set:
   - `approved: true`
   - non-empty `reviewer`
   - exact `attribution`
   - allowed relative target path
4. Leave untrusted, unread, adapter-only, reference-only, or deferred rows unapproved.
5. Re-run apply in dry/refusal mode if needed to confirm unapproved packets refuse cleanly.

## Structured output

Emit or persist this compact step log:

```json
{
  "step": 4,
  "name": "keep/update/remove packet",
  "source": "owner/repo",
  "status": "review_pending|done|blocked",
  "evidence": {
    "content_packet": "/tmp/<review-root>/content-packet.json",
    "draft_ops": 0,
    "approved_ops": 0,
    "unapproved_ops": 0,
    "applyable": false
  },
  "next_step": 5,
  "next_command": "run the apply stage for <owner/repo> with the approved /tmp/<review-root>/PROPOSED-CHANGE.md packet"
}
```

## Discipline

This step is the approval boundary. Do not auto-approve generated stubs. Do not treat candidate suggestions as content. If exact content, reviewer, and attribution are missing, the correct status is `review_pending` or `blocked`, not `done`.