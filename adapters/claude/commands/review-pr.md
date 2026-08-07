# /review-pr

## Purpose

Review a PR-ready diff with merge-quality discipline.

## Procedure

1. Inspect the diff, not just the final files.
2. Check correctness, regressions, security, tests, and docs.
3. State whether the branch is ready to merge.

## Required output shape

- **PR Scope**
- **Blocking Issues**
- **Non-Blocking Notes**
- **Merge Verdict**

## Final reporting

After the command-specific output, end the run with the standard final report headings from `rules/10-reporting-format.md` unless the operator asked for a different deliverable shape.

## Provenance

- Source: local Claude-OC-System default command inventory plus internal Hermes-operator adaptation.
- Disposition: runtime-specific-adapter for Claude Code default.
- Notes: exposes shared default behavior as Claude slash-command workflow surface.
