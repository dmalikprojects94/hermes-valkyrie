---
name: hermes-update-terminal-loadout-readiness
description: "Use when a Hermes Agent update may affect the terminal loadout system; launches a structured readiness audit in Claude Code or Codex."
version: 1.0.1
author: operator
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [hermes, update, loadout, claude-code, codex, readiness]
    related_skills: [coding-terminal-loadout-system, hermes-agent, coding-agent-prompt-enhancer]
---

# Hermes Update Terminal Loadout Readiness

## Overview

Use this skill when an operator wants to check whether a Hermes Agent update will break or drift the terminal loadout system.

This skill is self-contained. It does not require any development-only prompt packet or non-public folder. The coding runtime should run a structured readiness loop: snapshot the current state, compare the updated Hermes candidate against the previous stable baseline and repo-owned overlays, classify diff impact, adapt only missing pieces, and verify the terminal loadout system end to end.

Do not treat this as a blind reimplementation script. The correct loop is diff-driven reconciliation: preserve what still works, adopt upstream when it absorbed the behavior, and only reapply custom patches when the candidate is missing or broke a required feature.

## When to Use

Use this when the operator says:

- "after Hermes update, make sure the terminal loadout system still works"
- "run the Hermes update readiness check"
- "use /goal to check the loadout system after update"
- "compare the current Hermes setup to the updated Hermes version"
- "reintegrate the terminal loadout system into the new Hermes Agent"

Do not use for ordinary app repo work. Use `coding-terminal-loadout-system` for normal Claude/Codex launches.

## Source of Truth

Terminal loadout repo:

```text
<terminal-loadout-repo>
```

Hermes profile or sandbox under review:

```text
<hermes-profile-or-sandbox>
```

Repo-owned public control-plane files to compare:

```text
shared/
loadouts/
adapters/
hermes-gateway-skills/
scripts/
docs/
```

## Launch Pattern

Prefer Codex for the update-readiness implementation/audit unless the operator asks for Claude Code. Use the repo-managed visible terminal runner, not raw `codex`/`claude`.

1. Load `coding-terminal-loadout-system` and `coding-agent-prompt-enhancer`.
2. Create a task file in an operator-selected local workspace, or pass the task content through the managed runner's normal task-file path.
3. Launch a fresh visible session with `--keep-open-after-closeout` when the operator wants visible verification. Use `--stop-after-closeout` when the task is intended to auto-close after structured closeout.
4. Submit a `/goal <standing completion condition>` line plus a short follow-up telling the runtime to follow the task file.

Example enhanced task file content:

```text
/goal Run the Hermes update terminal-loadout readiness loop until every required check is classified PASS/FAIL/BLOCKED with evidence, and stop only after writing the final structured report.

Use the current repository as the terminal-loadout source of truth:
<terminal-loadout-repo>

Use this Hermes profile or sandbox as the candidate under review:
<hermes-profile-or-sandbox>

Do not update production Hermes, restart the gateway, overwrite live config, or commit secrets. Produce a readiness report with real command output and exact next actions.
```

Recommended runner command shape:

```bash
cd <terminal-loadout-repo>
python scripts/run_loaded_agent.py \
  --runtime codex \
  --loadout default \
  --repo <terminal-loadout-repo> \
  --task-file <task-file> \
  --label hermes-update-loadout-readiness \
  --watch \
  --watch-seconds 900 \
  --keep-open-after-closeout \
  --json
```

For Claude Code, change `--runtime codex` to `--runtime claude`. For Claude, never use ACP.

## Required Checks

The runtime must check:

1. Baseline capture: Hermes version, live checkout path/commit/status, profile config path, loadout repo HEAD/status, active profile, relevant env pointers.
2. Backup/snapshot: non-secret snapshot of config schema, enabled tools/toolsets, installed skills, and tracked repo control-plane files.
3. Candidate update analysis: isolated candidate only; never run production `hermes update` without explicit operator approval.
4. Diff classification: compare old/current Hermes and updated candidate; classify feature impact as `direct_hit`, `nearby_hit`, `no_hit`, or `unclear`.
5. Overlay reconciliation: compare live profile skills/config patches against the repo-owned public control-plane snapshot.
6. Terminal loadout verification: `validate_loadouts`, tests, command inventories for Claude and Codex, visible terminal launchability, hooks, watcher, closeout, save-destination/project report routing, and session cleanup behavior.
7. Decision: `READY`, `REPAIR_REQUIRED`, `BLOCKED`, or `DO_NOT_UPDATE`, with exact evidence.

## Safety Rules

- Do not run production `hermes update`.
- Do not restart production gateway.
- Do not overwrite live `config.yaml`; use `hermes config check`, `hermes config migrate` diagnostics, and sanitized patch proposals.
- Never print or commit secrets from env files, auth files, OAuth stores, tokens, browser profiles, or runtime artifacts.
- Do not commit local runtime homes, raw terminal captures, prompt scratch files, or generated output artifacts.
- Use the resolved runtime HOME for Claude/Codex CLI checks; do not hardcode an operator-specific home path.

## Completion Contract

The coding runtime is done only when it reports:

- runtime/loadout used;
- baseline Hermes version and candidate version/commit if available;
- files/diffs inspected;
- checks run with real output;
- pass/fail/blocker table;
- exact remediation patches or commands needed;
- whether live gateway skill behavior matches repo snapshot;
- whether config patching is needed;
- whether reports routed to save destination/project mirror;
- whether the system is ready for update cutover.

## Provenance

- Source: terminal-loadout operating practice.
- Disposition: public-safe shared skill.
- Notes: runtime-portable shared skill for Hermes coding-terminal workflows.
