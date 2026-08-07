# Transfer Skill Builder

Build equivalent behavior when a feature exists naturally in one runtime but not the other. Preserve **intent, not syntax**.

## When to use

`runtime-parity-mapper` assigned `transfer-skill-needed` to a capability.

## Cases

- **Claude slash command → Codex skill/command-equivalent.** Re-express the command's behavior as a Codex `SKILL.md` (or command-equivalent doc).
- **Claude agent/subagent pattern → Codex instruction/skill pattern.** Capture the agent's role, inputs, and stop condition as a Codex instruction or skill.
- **Codex config behavior → Claude adapter/rule equivalent.** Re-express a `config.toml` behavior as a Claude rule, hook, or adapter.

## Steps

1. State the intent the source runtime delivers (what the user relies on), independent of syntax.
2. Choose the target surface: a shared skill if both runtimes can use one, otherwise a runtime-specific adapter.
3. Produce the proposal as a shared skill or runtime-specific adapter file (proposal only — wiring happens via a migration task pack).
4. Include a parity verification command so the equivalence is checkable.

## Hard rules

- Preserve intent; do not blindly imitate the source runtime's syntax.
- Output is a shared skill **or** a runtime-specific adapter proposal, plus a parity test/inventory check.

## Verification

```bash
python scripts/list_runtime_commands.py --runtime claude --loadout <name>
python scripts/list_runtime_commands.py --runtime codex --loadout <name>
```

For update/management work, verify against `loadout-management` unless the migration task pack names a different target loadout.

## Provenance

- Source: internal Hermes-operator design; see the maintainer utility-skill audit notes (utility skill 5, not shipped publicly).
- Disposition: repo-resident onboarding utility skill; not wired into `default`; available through the explicit `loadout-management` loadout.
- Notes: companion to `runtime-parity-mapper`; converts parity gaps into equivalent-behavior plans.
