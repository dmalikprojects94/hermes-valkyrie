# /resume-session

## Purpose

Reload saved context and restate the next concrete action before continuing.

## Procedure

1. Read the saved context artifact first.
2. Verify whether the repo/runtime state still matches it.
3. Restate the first action you will take next.

## Required output shape

- **Loaded Context**
- **State Check**
- **Immediate Next Step**

## Final reporting

After the command-specific output, end the run with the standard final report headings from `rules/10-reporting-format.md` unless the operator asked for a different deliverable shape.

## Provenance

- Source: local Claude-OC-System default command inventory plus internal Hermes-operator adaptation.
- Disposition: runtime-specific-adapter for Claude Code default.
- Notes: exposes shared default behavior as Claude slash-command workflow surface.
