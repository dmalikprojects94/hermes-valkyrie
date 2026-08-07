# Prompt Optimizer

Advisory-only skill: tighten a task request before execution starts. Use when the operator's prompt is vague, sprawling, or ambiguous.

## Trigger

- Operator invokes `/prompt-optimize`.
- The runtime detects the request is ambiguous and would otherwise execute against a moving target.

## Pipeline

1. **Restate the request** in one sentence. If you cannot, the request is too ambiguous to act on — ask one clarifying question and stop.
2. **Surface assumptions** that the original prompt left implicit. List them.
3. **Identify scope drift risk.** Which adjacent things might get pulled in if the request stays loose? Name them and exclude them.
4. **Propose a tightened prompt** with: explicit deliverable, explicit out-of-scope, explicit verification.
5. **Return both versions** — original and tightened — so the operator can choose.

## Output shape

A 4-section advisory:

- **Restated** — one sentence.
- **Assumptions** — bullet list.
- **Out of scope** — bullet list.
- **Tightened prompt** — the rewritten version, ready to copy back.

## Discipline

- Advisory only. Do not start executing the tightened prompt — wait for operator approval.
- Do not invent requirements. If a constraint is not in the original prompt or repo context, mark it as an assumption.
- Keep the tightened prompt shorter than the original where possible. Tightening removes ambiguity, not adds ceremony.

## Provenance

- Source: local Claude-OC-System default skill surface plus internal Hermes-operator adaptation.
- Disposition: distilled-into-default.
- Notes: migrated as a shared runtime-portable skill for the solidified default loadout.
