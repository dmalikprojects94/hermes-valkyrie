# /model-route

## Purpose

Choose the right runtime or model posture for the task.

## Procedure

1. Classify the task type.
2. Pick the runtime/model with a short justification.
3. State when a different route would be better.

## Required output shape

- **Task Shape**
- **Recommended Route**
- **Why**
- **Fallback Route**

## Final reporting

After the command-specific output, end the run with the standard final report headings from `rules/10-reporting-format.md` unless the operator asked for a different deliverable shape.

## Provenance

- Source: local Claude-OC-System default command inventory plus internal Hermes-operator adaptation.
- Disposition: runtime-specific-adapter for Claude Code default.
- Notes: exposes shared default behavior as Claude slash-command workflow surface.
