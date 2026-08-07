# Prompt Prep Pipeline

Use this before implementation when the incoming request is loose or under-specified.

## Goal

Turn a vague operator request into a Claude-ready execution prompt without starting the implementation yet.

## Required workflow

1. Restate the request in one sentence.
2. List the assumptions that are currently implicit.
3. List the out-of-scope items that are likely to drift in unless excluded.
4. Add explicit deliverable expectations.
5. Add explicit verification expectations.
6. Produce the final tightened prompt.

## Required output shape

Use these exact headings:

## Restated

## Assumptions

## Out of Scope

## Deliverable

## Verification

## Tightened Prompt

## Discipline

- Advisory only unless the operator tells you to proceed.
- Do not invent product decisions.
- If a key unknown changes the tool path, ask one clarifying question instead of pretending certainty.

## Provenance

- Source: internal Hermes-operator runtime-surface design.
- Disposition: runtime-specific-adapter for Claude Code baseline.
- Notes: baseline file copied into every Claude materialized loadout before named overlays.
