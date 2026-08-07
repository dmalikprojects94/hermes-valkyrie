# Architecture

How the Terminal Loadout System routes requests, layers loadouts, translates one
shared behavior definition into runtime-specific agent homes, and separates
materialization from managed launch.

## Core model

```text
operator/orchestrator
      │ loads deterministic Hermes skill
      ▼
hermes-gateway-skills/
      │ chooses managed workflow
      ▼
resolve_route.py ── loadout name
      │
      ▼
apply_loadout.py ── materialized runtime surface
      │
      ▼
managed launch wrapper / run_loaded_agent.py
      │
      ▼
visible proof + watcher + closeout + reportback
```

The system keeps five responsibilities separate: Hermes skill invocation, runtime choice, loadout choice,
runtime materialization, and launch supervision. That separation makes routes
deterministic, loadouts reusable, generated homes inspectable before anything
live reads them, and startup failures diagnosable.

## Read the architecture set

- [Routing Model](routing-model.md) — how a request becomes runtime, loadout, and launch-mode decisions.
- [Hermes Skill Control Plane](hermes-skill-control-plane.md) — how Hermes skills call the deterministic scripts, loadouts, adapters, watcher, and closeout path.
- [Loadout Inheritance](loadout-inheritance.md) — how `default` and specialty loadouts layer together.
- [Runtime Adapters](runtime-adapters.md) — how one shared loadout becomes Claude Code and Codex surfaces.
- [System Adoption Lifecycle](system-adoption-lifecycle.md) — how another system becomes reviewed loadout behavior.

## Operational contracts

- Always validate before materializing: `python scripts/validate_loadouts.py`.
- Prefer sandbox output first: `python scripts/apply_loadout.py --runtime claude --loadout <name> --output-root output`.
- Treat `hermes-loadout.json` as the generated surface's provenance record.
- Do not call Claude/Codex parity synchronized unless the user-facing behavior is equivalent or the gap is documented.
- Do not call an orchestrated startup visible unless the run has desktop-window proof, not only tmux attachment.

## Related documentation

- [Managed Visible Launch Contract](../guides/managed-visible-launch-contract.md) — startup/proof boundary.
- [Choosing a Loadout](../guides/choosing-a-loadout.md) — pick the right mode.
- [Live Home vs Output Mode](../guides/live-home-vs-output-mode.md) — choose a safe materialization target.
- [Prepare Claude and Codex](../tutorials/prepare-claude-and-codex.md) — inspect both runtime surfaces from one loadout.
- [Onboard a system into agents](../tutorials/onboard-a-system-into-agents.md) — run the adoption lifecycle in sandbox mode.
