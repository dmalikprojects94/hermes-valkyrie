# Source Ingestion Upgrade Loop

Consume the analysis loop's decision ledger plus explicit operator approval, author
**real** loadout skills/adapters/docs/tests from evidence, update source accounting in the
same commit, verify, and commit/push durable artifacts. This is the named upgrade half of
the two-loop ingestion surface.

Its defining discipline: **a placeholder, draft, or empty content op is never apply-ready.**
The pbakaus/impeccable ingestion failed here — a draft packet was mistaken for a completed
ingestion. This loop refuses that outcome.

This skill orchestrates existing mechanics (`source-ingestion-step-3..6`, the
`injection-review` and `apply-proposed-change` CLI). Do not re-derive their internals here.

## When to use

- The analysis loop produced an injection-prep bundle and the operator has filled decisions (approve/change/drop/defer with authored content + reviewer + attribution).
- The operator says "apply", "adopt for real", "upgrade the loadout", or "author the skill from that analysis".

## Inputs

- `prep_root`: the analysis loop's `output_root` (the injection-prep bundle).
- `decisions`: the filled `injection-decisions.template.json` (real content, reviewer, attribution per approved op).
- `output_root`: isolated root for the reviewed packet.

## Loop

1. **Review decisions.** Run the injection-review step against the exact bundle with the filled decisions file, into an isolated review root. (The injection-review automation lives in the maintainer development workspace and does not ship with the public repo; follow the steps manually or with your own tooling.)

2. **Refuse placeholders.** If `apply_ready` is false, STOP and report the actionable next step — do not apply, do not claim ingestion done. The machine-enforced pre-patch contract (`PREPATCH_CONTRACT`, schema `prepatch-contract/1`) drives this: `apply_ready: false` happens when any approved op has empty/draft/TODO/placeholder content, missing reviewer, missing attribution, missing target, missing body-read evidence, or is an `adapter-needed` surface without an `adapter_plan`/`canary`. That is the correct outcome for an underspecified packet; author the real content and re-run review.
3. **Author real content.** For every `add shared skill` / `patch existing skill` verdict, write the actual skill/adapter/doc/test body distilled from the read evidence — not a skeleton, not a TODO. Preserve intent, not upstream syntax. Re-run `injection-review` until it emits `REVIEWED-CHANGE.md` and `apply_ready: true`.
4. **Adapter gate.** Any `adapter-needed` verdict (hooks/CLI/browser/runtime) goes through a separate adapter path with a reversible canary. Never fold it into a blind bulk apply.
5. **Apply (gated).** Only after `apply_ready: true`, apply the reviewed change packet (`<review_root>/REVIEWED-CHANGE.md`).

6. **Account in the same change.** Update the source accounting the change touches:
   - your maintainer source-accounting ledgers (when adopting from an upstream GitHub repo);
   - the affected `docs/loadouts/<loadout>/CHANGELOG.md`;
   - regenerate capability/audit artifacts (below).
7. **Materialize + verify parity.** Materialize the target loadout for Claude and Codex and confirm equivalent behavior or a documented intentional gap.
8. **Verify.** Run validation and tests (below); paste real output.
9. **Commit/push durable artifacts only.** Never commit raw run artifacts or the isolated output roots. Push to origin/main only if verification passes.
10. **Closeout.** Report what was added, what was deferred, verification output, and remaining risks (use `source-ingestion-step-6-closeout`).

## Verification commands

```bash
python scripts/validate_loadouts.py
python scripts/apply_loadout.py --runtime claude --loadout <loadout> --output-root /tmp/<name>-claude --target-home --format json
python scripts/apply_loadout.py --runtime codex  --loadout <loadout> --output-root /tmp/<name>-codex  --target-home --format json
python scripts/smoke_clean_hermes_onboarding.py --json
git diff --check
```

Capability-matrix and audit-doc regeneration are maintainer-workspace tooling and do not ship publicly; skip them on a public checkout.

## Structured output

```json
{
  "loop": "source-ingestion-upgrade-loop",
  "source": "owner/repo",
  "apply_ready": false,
  "authored": ["shared/skills/<x>.md"],
  "deferred": ["<row>: <trigger>"],
  "accounting_updated": ["<maintainer source-accounting ledger>", "docs/loadouts/<loadout>/CHANGELOG.md"],
  "applied": false,
  "verification": ["validate_loadouts: pass", "smoke_clean_hermes_onboarding: pass"],
  "commit": "<sha-or-null>",
  "pushed": false,
  "remaining_risks": ["..."]
}
```

## Discipline

- Placeholder/draft/empty content is never apply-ready. If review says so, author real content or refuse with a concrete next step. Do not let a draft packet masquerade as a completed ingestion.
- No blind bulk imports. Hooks/CLI/browser/runtime adapters require a separate adapter path and a reversible canary.
- Only durable source/docs/tests get committed. Raw runtime artifacts and isolated output roots stay out of git.
- Own the synthesis: the final authored content and the decision to push are yours, not the tool's.

## Provenance

- Source: internal Hermes-operator runtime-surface design; consolidates the reviewed-ingestion Step 3–6 mechanics into a named operator loop.
- Disposition: distilled-into-loadout (loadout-management).
- Notes: named upgrade surface requested after pbakaus/impeccable, where a draft packet was nearly mistaken for a completed ingestion; the placeholder-refusal gate is the fix.
