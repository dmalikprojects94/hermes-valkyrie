# /save-session

## Purpose

Capture durable session context before pausing or handing off.

## Procedure

1. Summarize the mission, state, completed work, blockers, and next moves.
2. Reference files instead of duplicating large content.
3. Redact secrets and unstable junk.

## Required output shape

- **Mission**
- **Current State**
- **Artifacts**
- **Blockers**
- **Next Moves**

## Final reporting

After the command-specific output, end the run with the standard final report headings from `rules/10-reporting-format.md` unless the operator asked for a different deliverable shape.

## Provenance

- Source: local Claude-OC-System default command inventory plus internal Hermes-operator adaptation.
- Disposition: runtime-specific-adapter for Claude Code default.
- Notes: exposes shared default behavior as Claude slash-command workflow surface.
