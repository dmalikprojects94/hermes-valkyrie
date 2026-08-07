# /build-fix

## Purpose

Diagnose and fix build failures without guessing.

## Procedure

1. Capture the failing command and exact error.
2. Trace the failure to a concrete root cause.
3. Apply the narrowest fix that removes the failure.
4. Re-run the failing build or test.

## Required output shape

- **Failing Command**
- **Root Cause**
- **Fix Applied**
- **Verification**

## Final reporting

After the command-specific output, end the run with the standard final report headings from `rules/10-reporting-format.md` unless the operator asked for a different deliverable shape.

## Provenance

- Source: local Claude-OC-System default command inventory plus internal Hermes-operator adaptation.
- Disposition: runtime-specific-adapter for Claude Code default.
- Notes: exposes shared default behavior as Claude slash-command workflow surface.
