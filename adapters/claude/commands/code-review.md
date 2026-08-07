# /code-review

## Purpose

Review code for correctness, maintainability, and gaps before completion.

## Procedure

1. Read the actual changed files.
2. Look for logic bugs, missing tests, brittle assumptions, and cleanup debt.
3. Keep the review evidence-based, not stylistic fluff.

## Required output shape

- **Scope**
- **Findings**
- **Severity**
- **Suggested Fixes**

## Final reporting

After the command-specific output, end the run with the standard final report headings from `rules/10-reporting-format.md` unless the operator asked for a different deliverable shape.

## Provenance

- Source: local Claude-OC-System default command inventory plus internal Hermes-operator adaptation.
- Disposition: runtime-specific-adapter for Claude Code default.
- Notes: exposes shared default behavior as Claude slash-command workflow surface.
