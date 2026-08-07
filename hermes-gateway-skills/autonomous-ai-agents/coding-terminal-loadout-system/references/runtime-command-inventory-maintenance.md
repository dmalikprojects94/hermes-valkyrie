# Runtime Command Inventory Maintenance

Session learning: the operator wants slash-command visibility to be treated as a per-loadout invariant, not a one-off diagnostic. Claude Code and Codex both need inspectable command surfaces before launch.

## Durable repo document

The loadout repo should carry a durable inventory document:

```text
/home/<operator>/projects/<GITHUB_REPO_NAME>/docs/runtime-slash-command-inventories.md
```

That document should summarize how Claude and Codex command surfaces work and include inventory tables for every current loadout.

## Verification commands

Run these from the loadout repo whenever command bindings or loadouts change:

```bash
python scripts/list_runtime_commands.py --runtime claude --loadout <loadout>
python scripts/list_runtime_commands.py --runtime codex --loadout <loadout>
python scripts/validate_loadouts.py
python scripts/smoke_clean_hermes_onboarding.py --json
```

`apply_loadout` should materialize both of these into the runtime home:

```text
command-inventory.json
command-inventory.md
```

## Update rule

For every loadout, if the operator can ask for a slash-command-like capability in that loadout, the inventory must show it before launch. Do not rely on memory, old docs, or assumptions.

For Claude Code, repo-managed slash commands come from `adapters/claude/commands/*.md`, are registered in `adapters/claude/registry.yaml`, and are included by the selected loadout or inheritance chain.

For Codex, native runtime-owned slash commands are tracked in `adapters/codex/commands.yaml`; Hermes-managed command equivalents are exposed as skills from `shared/skills/` or loadout-specific skill paths.

## Pitfall

Do not only update the default loadout. the operator explicitly wants one of these command inventory surfaces for every loadout, so all current loadouts should be documented and future loadouts should be added to the inventory doc as part of the same change.