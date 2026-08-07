# Repo Full Pass

Command-equivalent skill for Codex and shared runtime parity for Claude's `/repo-full-pass` operator command.

## Goal

Run the Loadout Ingestion Pipeline through audit plus prepare, then stop at an approval gate unless an approved proposed-change packet is supplied. This is the review path for turning a repo audit into a staging bundle without unsafe live writes.

## Preferred process

The repo-pipeline automation for this workflow lives in the maintainer development workspace and does not ship with the public repo; follow the steps manually or with your own tooling.

Run the full-pass mode against the target repo with an isolated review/staging output root. Only when the operator supplies an explicitly approved proposed-change packet does the pass continue into apply.

## What it does

1. Runs the same analysis gate used by repo audit.
2. Builds an isolated review bundle with `PROPOSED-CHANGE.md`, `content-packet.json`, `staging-manifest.json`, `REVIEW.md`, proposed stubs, and preview accounting/changelog files.
3. Keeps all draft ops unapproved by default, so nothing is applyable until exact content is authored and approved with attribution.
4. Runs the apply path only when an approved `--proposed-change` is supplied.
5. Reports slash-command-shaped JSON for operator review.

## Runtime parity rule

Every suggested implementation should be evaluated for both Claude Code and Codex. Prefer a shared skill/instruction when the behavior is portable. Use `adapters/claude/` or `adapters/codex/` only for runtime projection details. If a feature can only land for one runtime, document the gap and the reason in the staging review before approval.

## Fallback/debug path

When the wrapped full pass misbehaves, run its raw stages one at a time — prepare into the review directory, then apply with the approved doc — and validate with:

```bash
python scripts/validate_loadouts.py
python scripts/smoke_clean_hermes_onboarding.py --json
```

## Provenance

- Source: Loadout Ingestion Pipeline operator command parity work.
- Disposition: shared Codex command-equivalent skill plus Claude command parity reference.
- Notes: mirrors `adapters/claude/commands/repo-full-pass.md`; the pipeline backend is shared maintainer tooling.
