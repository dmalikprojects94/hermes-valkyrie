# /repo-audit

## Purpose

Run the GitHub-repo-to-loadout pipeline in audit mode. This command reviews a repo, writes/reads the existing audit artifacts, and reports what would be implemented without making live loadout changes.

Parity rule: if the audit suggests a feature for Claude Code, also suggest the shared or Codex implementation path when possible. Prefer shared skills/instructions first, runtime adapters second, and explicit intentional-gap notes when parity is not possible.

## Inputs

Ask for or infer:

- `alias`: source-list alias, default `claude-stack`.
- `repo`: GitHub `owner/repo` or URL.
- `output_root`: optional isolated output root. Use `/tmp/<repo-slug>-repo-audit` for review-only runs unless the operator asks to write into the repo.

## Procedure

1. Confirm the repo and alias. If the repo is missing, ask only for that.
2. Work from the loadout-system repo:

   ```bash
   cd <terminal-loadout-repo>
   ```

3. Audit the upstream surface. Inspect the target repo directly (clone or fetch read-only) and inventory what it exposes: skills, slash commands, agents, hooks, MCP wiring, instruction files, and config. Record counts and file paths into `<output_root>` as a surface-analysis note.

4. Compare against the current loadout system. For each upstream surface item, note whether an equivalent already exists in `shared/`, `loadouts/`, or `adapters/`, and mark it as candidate-adopt, redundant, or reject.

5. Draft the integration plan. For each candidate, state the routing (shared skill/instruction first, runtime adapter second, intentional-gap note when parity is not possible), the target loadout, and the files that would change. Write the plan into `<output_root>`; make no live loadout writes.

6. Summarize the unified adoption picture: what would be admitted, routed, rejected, or left upstream, with evidence paths for each claim.

7. Read your generated notes/summaries before replying. Do not claim counts from memory.

Note: Registry automation for this workflow is maintainer development-workspace tooling and does not ship with the public repo.

## Required output shape

Report concisely with these headings:

- **Mode:** audit; no live loadout writes.
- **Repo:** `<owner/repo>` and inspected revision if available.
- **Artifacts:** paths to the Step 1 surface-analysis and integration-plan docs/JSON.
- **Step 1 counts:** rows, surface-kind counts, tool-map count, command-map count, slash command files, slash commands.
- **Implementation preview:** what would be admitted, routed, rejected, or left upstream.
- **Review asks:** exact items the operator should inspect before a full pass.
- **Next command:** the full-pass command to run if the audit is approved.

## Safety rules

- Audit mode never performs live loadout writes.
- Prefer isolated `--output-root /tmp/...` unless the operator explicitly wants repo docs updated.
- Do not bulk-import upstream files. Report candidate behavior and routing only.
- If a command fails, include the real failure and the next safe retry command.

## Final reporting

After the command-specific output, end the run with the standard final report headings from `rules/10-reporting-format.md` unless the operator asked for a different deliverable shape.

## Provenance

- Source: internal Hermes-operator GitHub repo loadout-adoption pipeline.
- Disposition: runtime-specific-adapter for Claude Code loadout-management.
- Notes: exposes the audit-mode stage (surface analysis, comparison, integration plan) of the repo-adoption pipeline as an operator slash command.
