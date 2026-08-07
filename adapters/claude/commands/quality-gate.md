# /quality-gate

## Purpose

Run a final quality and risk gate before completion.

## Procedure

1. Check correctness, verification coverage, docs drift, and obvious risk.
2. Reject completion if the evidence is too weak.

## Required output shape

- **Scope**
- **Quality Checks**
- **Risks**
- **Go/No-Go**

## Final reporting

After the command-specific output, end the run with the standard final report headings from `rules/10-reporting-format.md` unless the operator asked for a different deliverable shape.

## Provenance

- Source: local Claude-OC-System default command inventory plus internal Hermes-operator adaptation.
- Disposition: runtime-specific-adapter for Claude Code default.
- Notes: exposes shared default behavior as Claude slash-command workflow surface.
