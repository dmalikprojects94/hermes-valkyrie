# Default Loadout Solidification Pattern

Use this reference when the operator asks to make the `default` loadout fully migrated, solidified, or stable before moving on to specialty loadouts.

## Intent

`default` is the inherited backbone. It should be stable, lean, source-accounted, and verified for both Claude Code and Codex. Specialty behavior belongs in named loadouts unless it passes the loadout-builder admission rule: broadly useful, low-context, low-ceremony, and safe as inherited behavior for every downstream loadout.

## Default solidification checklist

1. Inspect `loadouts/default/loadout.yaml` and identify every active frame file:
   - `shared_instructions`
   - `shared_skills`
   - `runtime_overrides.claude.commands`
   - `runtime_overrides.claude.agents`
   - `runtime_overrides.claude.hooks`
   - Claude/Codex `loadouts/<runtime>/Folder-Start/` baseline files.
2. Backfill provenance on every default frame file. Prefer a small `## Provenance` section for Markdown and a trailing comment block for code files. Capture source category, disposition, and notes.
3. Add/update a status document in the repo, e.g. `docs/default-loadout-solidification-status.md`, with:
   - what default covers now;
   - provenance coverage summary;
   - verification commands and observed outputs;
   - remaining work that is intentionally outside default.
4. Update durable overview docs such as `README.md` and `docs/migration-notes.md` so future agents see default as the stable inherited backbone.
5. Verify provenance coverage programmatically: collect the default frame files from YAML + registry + Folder-Start and assert each contains `Provenance`.
6. Run verification:
   - `python scripts/validate_loadouts.py`
   - `python scripts/smoke_clean_hermes_onboarding.py --json`
   - `python scripts/apply_loadout.py --runtime claude --loadout default --output-root /tmp/default-loadout-check --format json`
   - `python scripts/apply_loadout.py --runtime codex --loadout default --output-root /tmp/default-loadout-check --format json`
   - `python scripts/list_runtime_commands.py --runtime claude --loadout default`
   - `python scripts/list_runtime_commands.py --runtime codex --loadout default`
7. Check `git diff --check`, `git status --short`, and report uncommitted/untracked files separately. Do not commit unless the operator explicitly approves the specific commit.

## Provenance categories used for default

Keep categories plain and editable:

- local Claude-OC-System default backbone material distilled into Hermes;
- upstream GitHub sources already captured in source docs, such as `mattpocock/skills`;
- internal Hermes-operator runtime-surface design for new Hermes/Codex-specific behavior.

## Pitfalls

- Do not call default solidified until both runtime materialization and provenance coverage are verified.
- Do not let default absorb specialty posture just because it is useful. Route bulky or situational behavior to named loadouts.
- Be careful when using helper scripts to patch many files. Immediately read back one changed file and run the coverage check; if a helper ran in the wrong directory or did not persist writes, rerun from the repo root and verify with `git status`.
- Separate pre-existing untracked docs/artifacts from the files changed in the current pass when reporting status.
