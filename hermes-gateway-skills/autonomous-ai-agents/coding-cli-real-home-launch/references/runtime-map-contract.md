# Runtime-map-backed loadout integration notes

Use this when Hermes is consuming an external Claude/Codex loadout repo and the repo already has adapter runtime maps.

## Durable lesson

Treat `adapters/<runtime>/runtime-map.yaml` as executable contract, not descriptive metadata.

If the runtime map exists, it should drive:

- validator expectations
- materializer output paths
- manifest location
- operator-visible apply metadata

## Good implementation shape

- validator rejects missing/invalid runtime maps before apply succeeds
- materializers resolve managed paths from the runtime map rather than hardcoded `hooks/`, `mcp/`, `skills/`, or manifest filenames
- apply output reports `target_mode`, `runtime_managed_paths`, `manifest_path`, and explicit `managed_files`
- tests cover both preview/repo-local output and live-home output

## Why this matters

Without this, runtime maps drift into stale documentation while real behavior remains buried in code. Hermes then cannot reliably inspect or trust the runtime surface it just applied.

## Session example pattern

A successful upgrade in this class:

- loaded runtime maps during validation
- failed validation on malformed or missing runtime maps
- switched Claude/Codex materialization from hardcoded paths to runtime-map-managed paths
- expanded emitted manifest metadata so Hermes could inspect the exact write contract after apply
- added tests for repo-local and live-home apply modes
