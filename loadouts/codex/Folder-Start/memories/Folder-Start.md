# Folder-Start Codex Baseline

This memory is copied into every Hermes-managed Codex runtime home before loadout-specific material is applied.

- Preserve the resolved runtime `HOME` when launching from Hermes so CLI auth resolves correctly on the operator's setup.
- Keep generated outputs out of git; raw run evidence belongs in Obsidian or runtime artifact storage.
- Treat this folder as rebuildable baseline state, not a live Codex home backup.

## Provenance

- Source: internal Hermes-operator runtime-surface design.
- Disposition: runtime-specific-adapter for Codex baseline.
- Notes: baseline file copied into every Codex materialized loadout before named overlays.
