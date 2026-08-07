# Integrations

Optional integrations. The system runs without any of them; configure only what you need. All configuration comes from `.env` (template: `.env.example`).

| Integration | Use it when | Start here |
| --- | --- | --- |
| Orchestrator | Another process chooses runtime/loadout and supervises managed visible agent launch. | [Running Under an Orchestrator](hermes.md) |
| Managed launch proof | You need to prove a Claude/Codex terminal launched visibly and closed out correctly. | [Managed Visible Launch Contract](../guides/managed-visible-launch-contract.md) |
| Save destination | You want durable run reports copied outside the working tree to an Obsidian vault, notes folder, logs folder, or other writable directory. | [Operator personalization](../guides/operator-personalization.md) |
| Reportback | You want run closeouts posted back to a chat thread. | [Operator personalization](../guides/operator-personalization.md) |

## Configuration posture

- Keep every secret and operator-specific ID in `.env` or the shell environment.
- Leave optional integrations unset unless you need them.
- Validate and materialize in sandbox before connecting an orchestrator to a live runtime home.

## Related documentation

- [Running Under an Orchestrator](hermes.md) — programmatic resolve/apply/launch contract.
- [Reportback Integration](reportback.md) — portable closeout/reporting contract with environment-only transport examples.
- [Live Home vs Output Mode](../guides/live-home-vs-output-mode.md) — safe materialization targets.
- [Security](../SECURITY.md) — secret-handling policy.
