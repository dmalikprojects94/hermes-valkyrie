# /context-budget

## Purpose

Audit context growth and decide whether to compact or relaunch.

## Procedure

1. Measure current session sprawl.
2. Identify what context is still needed.
3. Decide whether to compact, hand off, or start fresh.

## Required output shape

- **Current Load**
- **Keep**
- **Drop**
- **Decision**

## Final reporting

After the command-specific output, end the run with the standard final report headings from `rules/10-reporting-format.md` unless the operator asked for a different deliverable shape.
