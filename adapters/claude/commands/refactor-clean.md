# /refactor-clean

## Purpose

Clean structure while preserving externally visible behavior.

## Procedure

1. State the behavior that must not change.
2. Make structural cleanup changes only.
3. Run regression checks after each cluster of edits.

## Required output shape

- **Behavior Guardrail**
- **Refactor Changes**
- **Regression Checks**
- **Residual Debt**

## Final reporting

After the command-specific output, end the run with the standard final report headings from `rules/10-reporting-format.md` unless the operator asked for a different deliverable shape.

## Provenance

- Source: local Claude-OC-System default command inventory plus internal Hermes-operator adaptation.
- Disposition: runtime-specific-adapter for Claude Code default.
- Notes: exposes shared default behavior as Claude slash-command workflow surface.
