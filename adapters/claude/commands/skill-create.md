# /skill-create

## Purpose

Package a reusable workflow or doctrine into a durable skill.

## Procedure

1. Capture trigger conditions.
2. Write numbered steps.
3. Record pitfalls and verification steps.
4. Prefer a reusable skill over session-only advice.

## Required output shape

- **Trigger**
- **Workflow**
- **Pitfalls**
- **Verification**

## Final reporting

After the command-specific output, end the run with the standard final report headings from `rules/10-reporting-format.md` unless the operator asked for a different deliverable shape.

## Provenance

- Source: local Claude-OC-System default command inventory plus internal Hermes-operator adaptation.
- Disposition: runtime-specific-adapter for Claude Code default.
- Notes: exposes shared default behavior as Claude slash-command workflow surface.
