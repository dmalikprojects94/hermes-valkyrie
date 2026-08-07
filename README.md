# Hermes Valkyrie

## Hermes Valkyrie = Loadouts + Managed Coding Terminals.

![version](https://img.shields.io/badge/version-0.1.0-blue)
![python](https://img.shields.io/badge/python-3.11-green)
![license](https://img.shields.io/badge/license-MIT-yellow)
![validation](https://img.shields.io/badge/public_validation-passing-brightgreen)

> Hermes Valkyrie gives Hermes the ability to manage coding-agent terminal sessions, giving operators a sandbox-first way to choose a runtime, apply the right loadout, and collect full lifecycle closeout evidence when the run finishes. In short: Hermes can launch Claude Code or Codex runs and manage them for the whole session.

## Prerequisites

Hermes Valkyrie is a Linux-first project. It has been developed and verified on **Ubuntu 26.04 LTS**. The public validation path should also work on current Ubuntu LTS systems when the same toolchain is installed, but Ubuntu 26.04 LTS is the only version this release has been directly tested on.

Required for public validation and sandbox materialization:

- **Python 3.11** — verified on Python 3.11.15. Python runs the validation, routing, materialization, smoke-test, and managed-launch scripts.
- **PyYAML** — install with `python -m pip install pyyaml`. This is required because loadout definitions are YAML files.
- **GNU Make** — verified on GNU Make 4.4.1. Make is useful for developer workflows and compatibility with the broader toolchain.
- **build-essential** — verified on Ubuntu package version 12.12ubuntu2.26.04.2. This provides the normal compiler/build baseline expected on Ubuntu development machines.

Required only for optional or live runtime behavior:

- **Node.js >=20** — verified on v24.16.0. Node is only needed for optional hook scripts, including JavaScript hooks under `shared/hooks/`.
- **Claude Code and/or Codex** — only required for real managed launches. You can still inspect, validate, resolve routes, and materialize sandbox loadouts without authenticated runtime CLIs.

Ubuntu compatibility guidance:

- **Ubuntu 26.04 LTS** — directly developed and tested for this release.
- **Ubuntu 24.04 LTS** — expected to work if Python 3.11, PyYAML, GNU Make, build-essential, and optional Node.js/Claude/Codex tools are installed.
- **Ubuntu 22.04 LTS** — expected to work with extra setup because Python 3.11 may not be the default system Python. Install Python 3.11 explicitly before running the validation commands.
- **Older Ubuntu releases** — not recommended unless you can provide Python 3.11 and a modern enough Node.js if you want hook support.
- **Non-Ubuntu Linux/macOS/WSL** — not the primary tested target for this release. The scripts are mostly portable Python, but managed terminal behavior, shell assumptions, and runtime CLI paths should be verified locally before relying on them.

## What it is

Hermes Valkyrie is a designed system for Hermes to control coding terminals, right now just Claude Code and Codex. It packages reusable coding-agent behavior (skills, hooks, MCP config, and more) into named loadouts, materializes those loadouts into runtime-specific files, and provides managed launches of these coding agents so the runs can be inspected, watched, closed out and responded to consistently instead of launched as one-off terminal sessions or not launched at all.

## Install For agents

Give this prompt to Hermes from a clean session:

```text
You are onboarding the Hermes Valkyrie repository from a clean session.

Goal: inspect, understand, and verify this repo as the Hermes-managed coding-terminal loadout system. Do not treat it as a generic Claude/Codex prompt pack. Your deliverable is a concise onboarding report with exact command outputs, generated manifest paths, verification results, blockers, and approval-gated next steps.

First, read these files before acting:

- README.md
- docs/README.md
- docs/INSTALL.md
- docs/architecture/hermes-skill-control-plane.md
- docs/architecture/routing-model.md
- docs/architecture/runtime-adapters.md
- docs/guides/managed-visible-launch-contract.md
- docs/guides/choosing-a-loadout.md
- docs/guides/troubleshooting.md

System model to understand and report back:

1. Hermes is the operator/orchestrator. It should not launch raw coding terminals directly when a managed loadout path exists.
2. Hermes bridge skills are the control plane. They decide when Hermes should invoke prompt enhancement, managed launch, visible launch proof, runtime-home guards, watcher/closeout, and final reportback.
3. Loadouts are the reusable behavior/context layer. They package skills, hooks, MCP guidance, commands, shared instructions, and runtime-specific overlays.
4. Adapters are deterministic runtime translators. They materialize the selected loadout into Claude-facing or Codex-facing files.
5. `coding-agent-prompt-enhancer` is a preflight step. Loose work should become a durable task prompt/task file with scope, deliverable, verification, closeout shape, and stop conditions before launch.
6. Launch must use the managed path, not raw `claude`, raw `codex`, ad-hoc tmux, or hidden one-off commands.
7. Closeout is a separate lifecycle stage: watcher state, structured report, artifact routing, verification evidence, then final Hermes/operator response.

Run inspect-only and sandbox checks from the repo root. Do not write into `~/.claude`, `~/.codex`, a live runtime home, a gateway profile, Discord, Slack, GitHub, email, or any external reportback target. Do not commit or push unless the operator explicitly asks. Do not add private paths, tokens, emails, Discord IDs, credentials, or operator-specific values to tracked files.

Commands to run:

1. `git status --short --branch`
2. `python scripts/validate_loadouts.py`
3. `python scripts/resolve_route.py --runtime claude --request "Use Claude Code for research" --explicit-loadout research`
4. `python scripts/resolve_route.py --runtime codex --request "Use Codex for research" --explicit-loadout research`
5. `python scripts/apply_loadout.py --runtime claude --loadout research --output-root output`
6. `python scripts/apply_loadout.py --runtime codex --loadout research --output-root output`
7. Inspect `output/claude/hermes-loadout.json` and `output/codex/hermes-loadout.json`; report runtime, loadout, inheritance chain, managed-file count, and generated skill/command surfaces.
8. `python scripts/list_runtime_commands.py --compare --loadout research --format markdown`
9. Create a durable dry-run task file under `output/onboarding/task.md`.
10. Run `python scripts/run_loaded_agent.py --runtime claude --loadout research --repo . --task-file output/onboarding/task.md --dry-run --json`.
11. Verify the dry-run command shape includes `run_loaded_agent.py`, `--runtime`, `--loadout`, `--task-file`, and `--json`; verify it does not use raw `claude`, raw `codex`, or ad-hoc tmux.
12. `git diff --check` if this is a git checkout.

Report back in this format:

- Repo path checked.
- Branch/commit if git repo.
- Docs read.
- Hermes/control-plane summary.
- Runtime/loadout decisions confirmed.
- Sandbox manifests generated with paths and managed-file counts.
- Managed-launch dry-run status.
- Verification outputs.
- Skipped by design: live-home writes, live runtime launch, external reportback, commit/push.
- Blockers, if any.
- Approval-gated next steps.

Stop and ask before any live-home apply, authenticated Claude/Codex launch, gateway/service restart, Discord/Slack/GitHub/email action, real `.env` secret write, commit, push, package publish, or public release.
```

## Installation Process

From a clean checkout, run the public-safe install/verification path:

```bash
python -m pip install pyyaml
python scripts/validate_loadouts.py
python scripts/resolve_route.py --runtime claude --request "Use Claude Code for research" --explicit-loadout research
python scripts/resolve_route.py --runtime codex --request "Use Codex for research" --explicit-loadout research
python scripts/apply_loadout.py --runtime claude --loadout research --output-root output
python scripts/apply_loadout.py --runtime codex --loadout research --output-root output
python scripts/smoke_clean_hermes_onboarding.py
```

Expected signals:

```text
loadouts valid
research
research
CLAUDE CODE | loadout: research | session: fresh | cwd: n/a
CODEX | loadout: research | session: fresh | cwd: n/a
clean_hermes_onboarding_smoke=PASS
```

After the commands finish, inspect `output/claude/hermes-loadout.json` and `output/codex/hermes-loadout.json`. If you only wanted sandbox validation, delete `output/` when done.

## What it does

Hermes Valkyrie separates agent operation into a few essential systems that can be tested independently and then composed into a managed launch.

| System | How it works |
| --- | --- |
| Runtime routing | The caller chooses `claude` or `codex`, then `scripts/resolve_route.py` resolves the requested loadout. Explicit `--explicit-loadout` selection wins over request text. |
| Loadouts | Each `loadouts/<name>/loadout.yaml` defines a behavior surface. Loadouts can share common instructions, commands, hooks, skills, and runtime-specific overlays. |
| Sandbox materialization | `scripts/apply_loadout.py` turns a loadout into runtime-specific files under `output/` by default, so generated behavior can be reviewed before live use. |
| Managed launch | `scripts/run_loaded_agent.py` launches Claude Code or Codex with a durable task file, selected loadout, watcher defaults, lifecycle tracking, and closeout extraction. |
| Validation | `scripts/validate_loadouts.py`, clean onboarding smoke tests, command inventory comparison, and the public GitHub Actions workflow prove that a clean checkout can route and materialize both runtimes. |
| Hermes bridge skills | `hermes-gateway-skills/` contains optional frozen skill snapshots that let Hermes call into this deterministic launcher without carrying private operator state. |

## Loadout Itinerary

| Loadout | Intended use |
| --- | --- |
| `default` | Stable inherited backbone for ordinary coding-agent runs. |
| `research` | Source review, documentation lookup, and evidence-first investigation. |
| `deep-coding` | Larger implementation work that needs stronger coding posture. |
| `coding` | General coding work with the standard coding behavior surface. |
| `project-planner` | Planning, decomposition, and implementation-roadmap work. |
| `writing-docs` | Documentation drafting, editing, and repo-facing writing tasks. |
| `media-video` | Media/video-oriented development and analysis workflows. |
| `frontend-design` | Frontend/UI implementation and design-focused passes. |
| `frontend-research-audit` | Frontend research, inspection, and audit passes. |
| `open-design` | Open-ended design exploration before implementation is locked. |
| `devops` | Infrastructure, deployment, and operations-oriented work. |
| `marketing` | Marketing, positioning, and public-facing copy work. |
| `loadout-management` | Maintaining, auditing, and extending the loadout system itself. |

## Project Tree

```text
.github/workflows/     Public-safe validation workflow for clean checkouts.
adapters/              Runtime-specific materialization maps and commands.
config/                Safe example configuration.
docs/                  Public documentation source tree.
examples/              Minimal example routing, loadout, and task files.
hermes-gateway-skills/ Optional frozen Hermes bridge skill snapshots.
loadouts/              Named loadout definitions and overlays. loadouts/<runtime>/Folder-Start/ holds the baseline runtime surface copied into every materialized loadout.
scripts/               Validation, route resolution, materialization, and managed-runner tools.
shared/                Reusable shared instructions, skills, hooks, and packs.
spec/                  Loadout schema.
```

## Documentation

Start with:

- [Documentation index](docs/README.md)
- [Install guide](docs/INSTALL.md)
- [Architecture overview](docs/architecture/README.md)
- [Routing model](docs/architecture/routing-model.md)
- [Runtime adapters](docs/architecture/runtime-adapters.md)
- [Managed visible launch contract](docs/guides/managed-visible-launch-contract.md)
- [Troubleshooting](docs/guides/troubleshooting.md)

Governance: [License](LICENSE) · [Contributing](docs/CONTRIBUTING.md) · [Security policy](docs/SECURITY.md)

The docs-folder overview in this source repo is named [Documentation overview](docs/DOCUMENTATION-OVERVIEW.md) so it is not confused with this root GitHub README.

## Safety

Hermes Valkyrie is sandbox-first. Do not commit local runtime homes, `.env` secrets, `.hermes/`, `.claude/`, `.codex/`, private prompts, generated output, vault paths, Discord IDs, or operator-specific state. Move from `output/` to a live runtime home only after explicit approval.

Hermes Valkyrie is an independent loadout and managed-terminal project for Hermes Agent operators. It is not affiliated with or endorsed by Nous Research, Anthropic, OpenAI, or any other runtime provider. Hermes Agent, Claude Code, Codex, and related provider names are referenced only to describe compatibility and operator workflows; users are responsible for complying with the terms for the tools they connect.

## Release

Current public launch milestone: **0.1.0**. See [CHANGELOG.md](CHANGELOG.md) for release history and version metadata.

Thank you so much for checking out my project. Please report any bugs or suggestions through the Issues feature in GitHub. This is my first open source project, and I use it every day, so I can't wait to see what it becomes.
