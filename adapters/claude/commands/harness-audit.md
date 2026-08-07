# /harness-audit

## Purpose

Inspect runtime configuration, hooks, and launch posture.

## Procedure

1. Inspect the active runtime files and manifests.
2. Check hooks, MCP, launch metadata, and session posture.
3. Name gaps between intended and actual runtime state.

## Required output shape

- **Runtime Surface**
- **Observed Wiring**
- **Gaps**
- **Recommendation**

## Final reporting

After the command-specific output, end the run with the standard final report headings from `rules/10-reporting-format.md` unless the operator asked for a different deliverable shape.
