# Claude/Codex Parity Mapper

Force every adopted capability through a Claude/Codex equivalence check. Same loadout name is **not** proof of parity — behavior must match or the gap must be explicit.

## When to use

Whenever a capability is proposed for adoption, before it is wired into any loadout.

## Parity statuses

- `shared` — one shared instruction/skill works for both runtimes.
- `adapted-one-to-one` — Claude and Codex have equivalent runtime-specific surfaces.
- `transfer-skill-needed` — one runtime lacks the native feature; build an equivalent (see `transfer-skill-builder`).
- `intentional-gap` — no safe equivalent; document the reason.
- `reject-unbalanced` — useful but would make one runtime too different.

## Steps

1. Define the shared intent first.
2. Map it to Claude (CLAUDE.md, commands, agents, hooks, MCP, skills) and Codex (skills, memories, config, baseline).
3. Assign a parity status. Any `transfer-skill-needed` generates a transfer-skill task.
4. Run the command/capability inventory check for **both** runtimes (see `command-capability-parity-verifier`).
5. Update command inventory / capability docs with the accepted mapping.

## Inventory checks (required, both runtimes)

```bash
python scripts/list_runtime_commands.py --runtime claude --loadout <name>
python scripts/list_runtime_commands.py --runtime codex --loadout <name>
```

## Hard rules

- Do not call a loadout synchronized just because both runtimes have the loadout name.
- Missing runtime equivalents become transfer-skill tasks, not silent gaps.

## Related skills

- `transfer-skill-builder` — build equivalent behavior across runtime differences.
- `command-capability-parity-verifier` — verify exposed commands/skills match intended behavior after materialization.

## Verification

```bash
python scripts/validate_loadouts.py
python scripts/list_runtime_commands.py --runtime claude --loadout <name>
python scripts/list_runtime_commands.py --runtime codex --loadout <name>
```

## Provenance

- Source: internal Hermes-operator design; see the maintainer utility-skill audit notes (utility skill 4) and the loadout synchronization contract (not shipped publicly).
- Disposition: repo-resident onboarding utility skill; not wired into `default`; available through the explicit `loadout-management` loadout.
- Notes: turns one-to-one runtime behavior into an explicit gate.
