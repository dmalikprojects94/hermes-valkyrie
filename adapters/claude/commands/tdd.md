# /tdd

## Purpose

Run the task in a strict red-green-refactor loop.

## Procedure

1. Write or identify the failing test first.
2. Run the failing test and capture the failure mode.
3. Make the minimum code change to pass.
4. Re-run the tests and only then refactor.

## Required output shape

- **Failing Test**
- **Minimal Change**
- **Passing Result**
- **Refactor Notes**

## Final reporting

After the command-specific output, end the run with the standard final report headings from `rules/10-reporting-format.md` unless the operator asked for a different deliverable shape.

## Provenance

- Source: local Claude-OC-System default command inventory plus internal Hermes-operator adaptation.
- Disposition: runtime-specific-adapter for Claude Code default.
- Notes: exposes shared default behavior as Claude slash-command workflow surface.
