# Loadout integration for real-HOME coding CLI launches

## Session takeaway

The durable rule in this environment is not just "launch Claude/Codex with `HOME=/home/<operator>` manually." When a Hermes loadout system exists, this rule should live inside that system as runtime launch metadata, and the Hermes integration layer should stay thin.

## Recommended representation

For both `claude` and `codex`, store a `launch` block with:

- `env.HOME: /home/<operator>`
- `command_prefix: export HOME=/home/<operator>`
- runtime-specific examples
- a short note explaining why the gateway profile home is wrong for standalone CLI auth

For Codex launchers that materialize a managed runtime home, also preserve:

- `CODEX_HOME=<applied runtime home>` at launch time

## Hermes shim pattern

Keep the split clean:

- external loadout repo = routing, inheritance, merge logic, materialization, manifest shape
- Hermes = thin caller / operator surface / runtime launcher

Recommended Hermes surfaces:

- `hermes loadout status`
- `hermes loadout resolve`
- `hermes loadout apply`
- `hermes loadout launch`
- `terminal_agent` for one-shot agent-facing runtime dispatch

## Safe verification pattern

1. Validate the external repo first.
2. Back up `~/.claude` and `~/.codex` before the first live `--target-home` apply.
3. For dry-run launch previews, materialize into a temporary output root instead of the live runtime homes.
4. Inspect the emitted `hermes-loadout.json` manifest.
5. Confirm `launch.env.HOME=/home/<operator>` is present.
6. Confirm Codex launch wiring sets `CODEX_HOME` to the applied runtime home.
7. Only then run a real live-home apply.

## Why this matters

If the rule exists only in prose or memory, Hermes can still regress into testing or launching against the gateway sandbox home and produce false "not logged in" or auth-failure results.

If dry-run touches the live runtime homes, verification itself can become a destructive action.

Putting the launch contract in the loadout manifest makes it available to:

- runtime launchers
- dry-run JSON inspection
- generated runtime docs
- tests
- rollback-aware operational procedures

## Example expectation

Claude manifest fragment:

```json
"launch": {
  "env": {"HOME": "/home/<operator>"},
  "command_prefix": "export HOME=/home/<operator>"
}
```

Codex manifest fragment:

```json
"launch": {
  "env": {"HOME": "/home/<operator>"},
  "command_prefix": "export HOME=/home/<operator>"
}
```

Codex launch environment expectation:

```text
HOME=/home/<operator>
CODEX_HOME=<applied runtime home>
```
