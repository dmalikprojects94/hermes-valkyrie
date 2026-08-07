# Command Inventory / Capability Parity Verifier

Verify the commands/skills a loadout exposes match its intended capability set — for both runtimes — after materialization.

## When to use

After any loadout change. Every loadout change updates command/capability inventory in the same pass.

## Inventory commands

```bash
python scripts/list_runtime_commands.py --runtime claude --loadout <name>
python scripts/list_runtime_commands.py --runtime codex --loadout <name>
```

## Generated inventory checks

After materialization, confirm the runtime home's generated `command-inventory.json` and `command-inventory.md` list the expected commands/skills for the loadout.

## Turning gaps into work

Any capability present in one runtime but missing in the other becomes a **transfer-skill task** (see `transfer-skill-builder`), not a silent gap.

## Hard rules

- Do not treat Claude and Codex command names as automatically equivalent; compare user-visible capability and expected behavior.
- Do not add missing capabilities directly during this check. Record the gap and hand it to `transfer-skill-builder` or a migration task pack.
- Use `loadout-management` for source/update management checks unless the work targets a specific specialty loadout.

## Verification

```bash
python scripts/list_runtime_commands.py --runtime claude --loadout default
python scripts/list_runtime_commands.py --runtime codex --loadout default
python scripts/list_runtime_commands.py --runtime claude --loadout loadout-management
python scripts/list_runtime_commands.py --runtime codex --loadout loadout-management
python scripts/validate_loadouts.py
```

## Provenance

- Source: internal Hermes-operator design; see the maintainer utility-skill audit notes (utility skill 10, not shipped publicly).
- Disposition: repo-resident onboarding utility skill; not wired into `default`; available through the explicit `loadout-management` loadout.
- Notes: companion gate to `runtime-parity-mapper`.
