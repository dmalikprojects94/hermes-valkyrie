# Hermes Skill Control Plane

The Terminal Loadout System has three deterministic layers:

1. **Hermes skills** decide how Hermes should invoke the coding-terminal system.
2. **Loadouts** decide what operating surface a runtime should receive.
3. **Adapters** translate that surface into Claude Code or Codex files.

The Hermes skills are the caller-facing layer. They are what Hermes loads when a user asks it to run Claude Code, run Codex, enhance a prompt, prove a visible launch, watch closeout, or report completion.

```text
Hermes session
    │
    ▼
Hermes skill from hermes-gateway-skills/
    │
    ▼
reviewed slash-command / managed-launch workflow
    │
    ▼
scripts/run_loaded_agent.py
    │
    ▼
loadouts/<name>/loadout.yaml
    │
    ▼
adapters/claude/ or adapters/codex/
    │
    ▼
Claude Code or Codex terminal run
    │
    ▼
watcher, closeout report, artifact routing
```

## Why the skills ship with the repo

A public reviewer needs to see more than `loadouts/` and `adapters/`. Those folders show the deterministic design, but the Hermes skills show the orchestration behavior that calls the design.

The repo therefore includes `hermes-gateway-skills/` as a versioned snapshot of the Hermes-facing skills that govern coding-terminal work.

Tracked skills include:

| Skill | Role in the system | Calls into | Update posture |
| --- | --- | --- | --- |
| `coding-terminal-loadout-system` | Canonical managed-launch executor. It routes Hermes coding-agent work into the repo-managed launch system instead of raw terminal starts. | `scripts/run_loaded_agent.py`, `scripts/coding_terminal_runner.py`, loadout resolution, watcher/closeout/reporting. | Frozen snapshot; update by reviewed commit only. |
| `coding-agent-prompt-enhancer` | Preflight prompt enhancer. It converts a loose user request into a durable launch prompt with scope, deliverable, runtime/loadout hints, verification, and closeout expectations. | `scripts/prompt_manager.py`, task-file creation, managed launch inputs. | Frozen bridge behavior; enhancer templates can grow through reviewed slash-command/setup flows. |
| `coding-cli-real-home-launch` | Real runtime-home guard. It ensures Claude Code/Codex launches use the intended authenticated CLI home, not a sandboxed gateway home, when live-home launch is explicitly approved. | runtime-home resolution, environment preparation, managed launch command construction. | Frozen guardrail; no self-update from launched terminals. |
| `claude-code-loadout-disclosure` | Visible-launch disclosure. It makes Hermes resolve and announce the Claude runtime/loadout before starting an observable terminal session. | loadout resolver, managed terminal launch proof, operator-facing launch notice. | Frozen proof contract. |
| `claude-code` | Hard router for Claude Code requests. It prevents raw direct Claude launch and routes through the managed loadout system. | managed Claude launch path and Claude adapter. | Frozen router. |
| `codex` | Hard router for Codex requests. It prevents raw direct Codex launch and routes through the managed loadout system. | managed Codex launch path and Codex adapter. | Frozen router. |

These skills are not generic knowledge notes. They are the Hermes-side API contract for this project. If a skill says a launch must go through `run_loaded_agent.py`, the deterministic scripts must keep that path working, documented, and tested.

## Flat deterministic skills, growing command surface

The Hermes gateway skills are intentionally flat. They are bridge/control-plane skills, not an ambient self-improving knowledge base.

They must not self-update during a managed coding-terminal run. A running Claude Code or Codex session should not patch the Hermes skills that launched it.

Growth should happen through reviewed surfaces:

- new slash-command behavior;
- new or changed loadouts;
- new shared skills or packs;
- deterministic adapter updates;
- source-accounted ingestion commits.

That gives the project two lanes:

| Lane | Changes how? |
| --- | --- |
| Deterministic Hermes skills | Reviewed snapshot commits only. |
| Growing setup/loadout library | New slash commands, shared skills, packs, source-accounted loadouts, tests. |

## Auxiliary impact through the workflow

Hermes skills affect every stage around the deterministic scripts:

| Stage | Hermes skill impact | Deterministic repo layer |
| --- | --- | --- |
| Intake | Decide whether this is Claude Code, Codex, prompt enhancement, or loadout-management work. | `scripts/resolve_route.py`, `loadouts/*/loadout.yaml` |
| Prompt prep | Turn the user request into a durable task file with scope and verification expectations. | `scripts/prompt_manager.py` |
| Launch | Require managed launch instead of raw `claude`, raw `codex`, or ad-hoc tmux. | `scripts/run_loaded_agent.py`, `scripts/coding_terminal_runner.py` |
| Materialization | Ensure the selected runtime receives the selected loadout. | `scripts/apply_loadout.py`, `adapters/*` |
| Runtime behavior | Carry skill, command, rule, hook, and memory surfaces into Claude/Codex. | `shared/`, `loadouts/`, `adapters/` |
| Closeout | Watch completion, extract report, route artifacts, and produce one final status. | `scripts/record_runtime_event.py`, `scripts/report_extractor.py`, `scripts/artifact_router.py` |
| Maintenance | Source-account changes and loadout updates instead of silent self-mutation. | `loadouts/*/SOURCES.md`, public source-accounting docs |

## Review rule

If a Hermes skill changes the way terminal agents launch, watch, close out, or report, that change belongs in the same review path as loadout and adapter changes: update the snapshot, update docs, run validation, and commit the diff.
