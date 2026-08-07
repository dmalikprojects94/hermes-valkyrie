# /repo-full-pass

## Purpose

Run the GitHub-repo-to-loadout pipeline as a full pass: audit the repo, prepare the adoption packet, apply an approved safe packet when available, validate the loadout system, then produce a post-implementation review.

Parity rule: every prepared implementation should be evaluated for both Claude Code and Codex. Prefer shared surfaces when portable; use runtime-specific adapters only for projection details; document any one-runtime gap before approval.

## Inputs

Ask for or infer:

- `alias`: source-list alias, default `claude-stack`.
- `repo`: GitHub `owner/repo` or URL.
- `mode`: `sandbox` by default; `live` only when the operator explicitly asks for live repo writes.
- `proposed_change`: optional path to an already-approved proposed-change doc/packet.
- `output_root`: optional isolated output root, default `/tmp/<repo-slug>-repo-full-pass` for sandbox runs.

## Procedure

1. Confirm repo, alias, and whether this is sandbox or live. If live was not explicitly requested, use sandbox.
2. Work from the loadout-system repo:

   ```bash
   cd <terminal-loadout-repo>
   ```

3. Analysis stage: audit the upstream repo's surface (skills, commands, agents, hooks, MCP, instructions, config), inventory what it exposes with counts and file paths, and write the surface-analysis evidence into `<output_root>` — the same Step 1 evidence audit mode produces.

4. Comparison: for each upstream surface item, note whether an equivalent already exists in `shared/`, `loadouts/`, or `adapters/`, and mark it candidate-adopt, redundant, or reject.

5. Prepare stage: draft the integration/proposed-change packet into `<output_root>`. For each candidate, name the routing (shared first, runtime adapter second, intentional-gap note otherwise), the target loadout, and the exact files that would change. No live loadout writes yet.

6. Apply stage: only if a proposed-change path is supplied and operator-approved, apply the packet by editing the named files under `loadouts/`, `shared/`, and `adapters/` exactly as the packet specifies (sandbox `--output-root` copies for sandbox mode; the live tree only in live mode).

7. If no approved proposed-change path exists, do not fake implementation. Report the prepared packet and stop at the approval gate.
8. Validate after any apply stage:

   ```bash
   python scripts/validate_loadouts.py
   python scripts/smoke_clean_hermes_onboarding.py --json
   ```

Note: Registry automation for this workflow is maintainer development-workspace tooling and does not ship with the public repo.

9. Inspect `git status --short` and `git diff --stat` before replying.
10. Produce the post-implementation review even if the pass stopped at the approval gate.

## Required output shape

Report concisely with these headings:

- **Mode:** full-pass sandbox or full-pass live.
- **Repo:** `<owner/repo>` and inspected revision if available.
- **Stages run:** analysis, prepare, apply if supplied/approved, validation.
- **Artifacts:** generated report, integration plan, proposed-change packet, apply report if any.
- **Implemented:** files/loadouts/skills/adapters changed, or `none — stopped at approval gate`.
- **Rejected/left upstream:** important surfaces intentionally not imported.
- **Validation:** exact commands and results.
- **Post-implementation review:** what landed, why it was admitted, what the operator should inspect, rollback notes.
- **Git state:** clean/dirty plus diff summary.

## Safety rules

- Sandbox is the default full-pass mode.
- Live writes require explicit operator direction or an approved proposed-change packet.
- Never invent an apply result. If the approval gate blocks apply, report that as the result.
- Do not commit or push unless the operator asked for the live full pass to include closeout.

## Final reporting

After the command-specific output, end the run with the standard final report headings from `rules/10-reporting-format.md` unless the operator asked for a different deliverable shape.

## Provenance

- Source: internal Hermes-operator GitHub repo loadout-adoption pipeline.
- Disposition: runtime-specific-adapter for Claude Code loadout-management.
- Notes: exposes the full-pass stages (analysis, prepare, gated apply, validation) of the repo-adoption pipeline as an operator slash command.
