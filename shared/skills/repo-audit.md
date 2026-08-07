# Repo Audit

Command-equivalent skill for Codex and shared runtime parity for Claude's `/repo-audit` operator command.

## Goal

Run the Loadout Ingestion Pipeline in read-only audit mode for a GitHub repository. This should surface what the repo might contribute to the Hermes loadout system without writing live loadout files.

## Preferred process

The repo-pipeline automation for this workflow lives in the maintainer development workspace and does not ship with the public repo; follow the steps manually or with your own tooling.

Run the audit-mode pass for the target repo against a source-list alias. Default alias is usually `claude-stack` unless the operator gives a different source-list context.

## What it does

1. Normalizes the repo reference.
2. Selects an existing comparison-ready source report, or generates surface analysis when explicitly requested and GitHub tooling is available.
3. Compares upstream surfaces against local loadout capabilities.
4. Reports evaluation decisions, candidate suggestions, blockers, artifacts, and the next command.
5. Performs no live loadout writes and stages no applyable content.

## Runtime parity rule

If this audit suggests a feature for Claude Code, also suggest the matching Codex implementation path when possible. Prefer shared skills/instructions first, then runtime-specific adapters. If parity is not possible, mark the gap explicitly as `intentional-gap`, `missing-claude`, or `missing-codex` rather than silently making a one-runtime recommendation.

## Fallback/debug path

When the wrapped audit pass misbehaves, run its raw stages one at a time — analysis only, then surface analysis, then integration planning — so each stage's output can be inspected in isolation.

## Provenance

- Source: Loadout Ingestion Pipeline operator command parity work.
- Disposition: shared Codex command-equivalent skill plus Claude command parity reference.
- Notes: mirrors `adapters/claude/commands/repo-audit.md`; the pipeline backend is shared maintainer tooling.
