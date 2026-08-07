# /plan

## Purpose

Turn the request into an execution-ready implementation plan before coding starts.

## Procedure

1. Restate the goal in one sentence.
2. Identify the files, systems, or repos that matter.
3. Break the work into ordered tasks with verification per task.
4. Call out unknowns before implementation starts.

## Required output shape

- **Plan Summary**
- **Task List**
- **Verification Plan**
- **Open Questions**

## Final reporting

After the command-specific output, end the run with the standard final report headings from `rules/10-reporting-format.md` unless the operator asked for a different deliverable shape.

## Provenance

- Source: local Claude-OC-System default command inventory plus internal Hermes-operator adaptation.
- Disposition: runtime-specific-adapter for Claude Code default.
- Notes: exposes shared default behavior as Claude slash-command workflow surface.
