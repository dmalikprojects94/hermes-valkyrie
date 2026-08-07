# Save Destination Output Routing

Decide where durable output belongs before you write it. This skill is runtime-neutral: it applies the same way under Claude Code and Codex.

## Routing rules

- **Code and project edits** belong in the project repository. Make the change in the repo, not in a note.
- **Non-project outputs** — research, analysis, diagnostics, scratch findings, anything that is information rather than a code change — belong in the raw save-destination lane as Markdown when a save destination is available.
  - Canonical lane: `$SAVE_DESTINATION_PATH/agents/<agent>/raw-runs/` (`claude` → `agents/claude-code/raw-runs`, `codex` → `agents/codex/raw-runs`).
  - `SAVE_DESTINATION_PATH` can be an Obsidian vault, a notes folder, a logs folder, or any normal writable directory.
  - `OBSIDIAN_VAULT_PATH` is still accepted as a legacy compatibility alias for existing Hermes deployments.
  - When no valid save destination is set, fall back to `<artifact_root>/raw/` and say so in your report.
- Raw output is **provenance**, not canonical memory. The terminal agent does not own the save destination as a source of truth; promotion of raw notes into durable project/daily notes is a separate, later step.

## Reporting

- Always mention any files you created and their full paths in the final `Changes` section.
- Keep the five-heading report contract exact: `Request`, `Changes`, `Verification`, `Blockers`, `Next Steps`.

## Secrets

- Never save secrets, tokens, keys, or credentials into reports, summaries, or provenance artifacts.
- If obvious credential text would land in a saved artifact, redact it as `[REDACTED]` before writing.

## Provenance

- Source: internal Hermes-operator operating practice.
- Disposition: distilled-into-default.
- Notes: runtime-portable shared skill for the operator's Hermes coding-terminal workflow.
