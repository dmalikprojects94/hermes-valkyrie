# Runtime Bootstrap

## Purpose

Define the Hermes-native SessionStart bootstrap contract used by runtime adapters.

This is distilled from the Superpowers v6.0.2 Claude/Codex hook parity pattern, but it is not a bulk import. Hermes keeps one shared intent and lets each runtime adapter express that intent through its own hook, config, memory, or native startup surface.

## SessionStart contract

At runtime start, resume, clear, or compact events, the adapter should make the active loadout visible before substantive work begins.

The bootstrap must expose:

- active loadout name and purpose;
- inherited shared instructions, skills, and packs;
- command or command-equivalent inventory;
- runtime-specific gaps or parity notes;
- source-accounted provenance for any imported/distilled behavior.

## Runtime event divergence

Claude and Codex are intentionally similar but not identical.

Claude uses a SessionStart-style adapter with events equivalent to `startup`, `clear`, and `compact`.

Codex uses a SessionStart-style adapter with events equivalent to `startup`, `resume`, and `clear`.

Do not force identical matcher names. Preserve the shared bootstrap intent and document runtime-specific event names in `adapters/<runtime>/runtime-map.yaml`.

## Safety rules

- Do not overwrite authentication, session databases, or unrelated plugin state.
- Do not load every upstream skill pack into default.
- Keep `default` lean; route repo-audit and source-accounting work to `loadout-management`.
- Runtime-specific syntax belongs in `adapters/<runtime>/`; reusable behavior belongs in `shared/`.

## Provenance

- Source: internal maintainer source-recheck notes on Superpowers (2026-06-18, not shipped publicly)
- Evidence: Superpowers `hooks/hooks.json`, `hooks/hooks-codex.json`, `hooks/session-start`, `hooks/session-start-codex`, `.codex-plugin/plugin.json`
- Disposition: distilled runtime bootstrap doctrine for Hermes adapters.
