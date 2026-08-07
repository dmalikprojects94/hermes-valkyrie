# Source Ingestion Step 2: Injection Review

Review the exact injection-prep bundle and decide what may proceed to the gated apply path.

## When to invoke

- Step 1 has produced a concrete injection-prep bundle.
- The operator asks to review what will be injected.
- A later agent needs approve/change/drop decisions for exact proposed ops.

## Pipeline

1. Consume the Step 1 injection-prep bundle: `injection-prep-*.md/json`, `PROPOSED-CHANGE.md`, `content-packet.json`, `staging-manifest.json`, and previews.
2. Refuse analysis-only inputs. A repo map/comparison ledger is not enough for Step 2.
3. Review each op for target path, operation type, content, provenance, parity, verification, rollback, source accounting, and changelog impact.
4. Mark each item: `approve`, `change`, `drop`, `defer`, `needs_source_body_review`, `adapter_needed`, or `reference_only`.
5. Only approved items with reviewer, attribution, verification, rollback, source revision, and exact content may be passed to the apply gate.

## Structured output

Emit or persist this compact step log:

```json
{
  "step": 2,
  "name": "injection review",
  "source": "owner/repo",
  "status": "review_pending|approved|changes_requested|blocked",
  "evidence": {
    "injection_review_markdown": "path-or-null",
    "injection_review_json": "path-or-null",
    "approved_ops": 0,
    "changes_requested_ops": 0,
    "dropped_ops": 0,
    "deferred_ops": 0,
    "blocked_ops": 0,
    "applyable": false
  },
  "next_step": "apply only if applyable=true and operator explicitly approves"
}
```

## Discipline

Step 2 answers: should this exact proposed injection proceed? It must not silently generate new prep work, hide incomplete evidence, or approve body-unread/path-only rows. Any missing content, missing attribution, missing reviewer, missing verification, missing rollback, or unresolved adapter/body-review issue keeps the packet unapplyable.
