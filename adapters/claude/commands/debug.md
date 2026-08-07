# /debug

## Purpose

Move from symptom to root cause deliberately.

## Procedure

1. Record the symptom precisely.
2. Reproduce it.
3. Inspect logs, state, and surrounding code.
4. Name the root cause before proposing a fix.

## Required output shape

- **Symptom**
- **Reproduction**
- **Root Cause**
- **Fix**
- **Verification**

## Final reporting

After the command-specific output, end the run with the standard final report headings from `rules/10-reporting-format.md` unless the operator asked for a different deliverable shape.

## Provenance

- Source: local Claude-OC-System default command inventory plus internal Hermes-operator adaptation.
- Disposition: runtime-specific-adapter for Claude Code default.
- Notes: exposes shared default behavior as Claude slash-command workflow surface.
