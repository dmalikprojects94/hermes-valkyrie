# Documentation

Documentation hub for the Terminal Loadout System, organized by intent. The docs
are designed to make the repo self-operating: a new human or coding agent should
be able to understand the system, validate it, materialize Claude Code/Codex
runtime homes, launch managed visible Claude Code/Codex sessions, extend loadouts, and verify a public-safe copy from this tree.

## Start here

- [README](../README.md) — human front door and value proposition.
- [Documentation Purpose](DOCUMENTATION-PURPOSE.md) — why these docs exist and what workflows they must fully enable.
- [Install](INSTALL.md) — human install modes and risk levels.
- [Your first loadout run](tutorials/first-loadout-run.md) — first sandbox materialization from clone to generated files.
- [Managed visible launch contract](guides/managed-visible-launch-contract.md) — required proof rules before claiming Claude/Codex launched visibly.

## Learn by doing

- [Tutorials](tutorials/README.md) — step-by-step walkthroughs.
- [First loadout run](tutorials/first-loadout-run.md) — validate, resolve, materialize, inspect.
- [Prepare Claude and Codex](tutorials/prepare-claude-and-codex.md) — compare generated runtime surfaces from one loadout.
- [Add a new loadout](tutorials/add-a-new-loadout.md) — create and verify a specialty overlay.
- [Onboard a system into agents](tutorials/onboard-a-system-into-agents.md) — turn a source system into reviewed sandbox behavior.

## Operate and customize

- [Guides](guides/README.md) — task-oriented guides.
- [Operator personalization](guides/operator-personalization.md) — environment placeholders and optional integrations.
- [Environment configuration](guides/environment-configuration.md) — `.env` design, setup modes, and optional variables.
- [Choosing a loadout](guides/choosing-a-loadout.md) — select the right mode before launch.
- [Live home vs output mode](guides/live-home-vs-output-mode.md) — move safely from sandbox to live runtime homes.
- [Managed visible launch contract](guides/managed-visible-launch-contract.md) — durable prompt file, managed runner, desktop-window proof, watcher, closeout, and reportback.
- [Troubleshooting](guides/troubleshooting.md) — symptom → command → bounded fix table.

## Understand the system

- [Architecture](architecture/README.md) — routing, inheritance, adapters, and provenance.
- [Routing model](architecture/routing-model.md) — deterministic runtime/loadout resolution plus explicit launch mode.
- [Loadout inheritance](architecture/loadout-inheritance.md) — default backbone plus specialty overlays.
- [Runtime adapters](architecture/runtime-adapters.md) — Claude Code and Codex materialization.
- [Hermes skill control plane](architecture/hermes-skill-control-plane.md) — Hermes skills that call the deterministic launch/loadout/adapter system.
- [System adoption lifecycle](architecture/system-adoption-lifecycle.md) — source review through approval and live adoption.
- [Public product repo shape](reference/public-product-repo-shape.md) — target folder structure and public/private boundaries for a distributable release.
- [Integrations](integrations/README.md) — optional orchestrator, capture, and reportback wiring.

## Governance

- [Contributing](CONTRIBUTING.md) — contribution workflow.

## Public release (maintainer note)

Upstream releases of this system are produced by extraction from the maintainer
development workspace: the release gate builds the public copy, scans it for
private markers, validates the loadouts, and materializes Claude plus Codex
sandbox outputs before anything is published. If you are reading this in the
public repo, that gate already ran — this tree is the release, and it is
designed to be fully usable without any maintainer-only assets.
