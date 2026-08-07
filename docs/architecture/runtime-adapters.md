# Runtime Adapters

A loadout is written once as shared intent. Runtime adapters translate that
intent into the concrete files each agent CLI actually reads. Claude Code and
Codex are sibling runtimes, not clones — the adapters keep them as
synchronized as practical without pretending they are identical.

```text
                 shared intent (runtime-neutral)
     ┌──────────────────────────────────────────────┐
     │  shared/instructions/*.md   durable posture  │
     │  shared/skills/*.md         reusable skills  │
     │  shared/packs/*/PACK.md     specialty bundles│
     │  loadouts/<name>/loadout.yaml  wiring        │
     └──────────────┬───────────────┬───────────────┘
                    │               │
             claude adapter   codex adapter
                    │               │
                    ▼               ▼
          output/claude/      output/codex/
          CLAUDE.md           skills/hermes-active-loadout/
          commands/*.md       selected shared skill folders
          agents/*.md         memories/hermes-loadout.md
          rules/*.md          config.toml (managed block)
          skills/*/SKILL.md   hermes-loadout.json
          hooks, MCP config
          hermes-loadout.json
```

## The rule: intent stays shared, expression stays runtime-specific

Canonical behavior lives in `shared/` and in each loadout's `loadout.yaml`.
Adapters own only the translation:

- **Claude Code** expresses behavior through `CLAUDE.md`, slash commands,
  subagents, rules, skills, hooks, and MCP configuration.
- **Codex** expresses the same behavior through skills, a managed memory
  note, and a managed `config.toml` block.

When you build or change a loadout, define the shared intent first, then map
it to each runtime. Never author behavior directly in an adapter that
belongs in `shared/`.

## What materialization writes

`apply_loadout.py` resolves the loadout (including its inheritance chain),
then hands the resolved definition to the adapter for the selected runtime.

| Surface | Claude output | Codex output |
| --- | --- | --- |
| Operating instructions | `CLAUDE.md` + `rules/*.md` | active-loadout skill + memory note |
| Commands | `commands/*.md` slash commands | command-equivalent skill docs |
| Subagents | `agents/*.md` | not native — documented gap |
| Skills | `skills/*/SKILL.md` | `skills/*/SKILL.md` |
| Hooks | hook scripts + wiring | runtime-native equivalents where they exist |
| Runtime config | MCP config | managed `config.toml` block |
| Manifest | `hermes-loadout.json` | `hermes-loadout.json` |

Both surfaces always include the manifest. It records the runtime, the
loadout, the `resolved_from` inheritance chain, and every managed file — so
any caller can inspect exactly what is active without diffing directories.

## Materialize both runtimes from one loadout

```bash
python scripts/apply_loadout.py --runtime claude --loadout research --output-root output
python scripts/apply_loadout.py --runtime codex  --loadout research --output-root output
```

Inspect both manifests:

```bash
python - <<'PY'
import json
from pathlib import Path
for runtime in ("claude", "codex"):
    m = json.loads(Path(f"output/{runtime}/hermes-loadout.json").read_text())
    print(runtime, m["loadout"], "->", len(m.get("managed_files", [])), "managed files")
PY
```

You should see one line per runtime naming the same loadout with a
runtime-appropriate file count:

```text
claude research -> <N> managed files
codex research -> <M> managed files
```

## Parity is tracked, not assumed

A loadout is not "synchronized" just because both runtimes accept its name.
Each behavior is classified:

- `synced` — both runtimes expose equivalent operator behavior.
- `shared-only` — the shared skill or instruction is enough on its own.
- `claude-only-acceptable` / `codex-only-acceptable` — one runtime has a
  native feature the other does not need for this workflow.
- `missing-claude` / `missing-codex` — a real gap that should be mapped.
- `intentional-gap` — parity is impractical; the reason is documented.

Runtime event models also differ (for example, session-start hook event
names are not identical across runtimes). Adapters preserve the shared
bootstrap intent and document the runtime-specific names instead of forcing
fake symmetry.

## Adapter boundary versus launch boundary

Adapters generate the files each runtime should see. They do not by themselves
prove that Claude Code or Codex started correctly. Orchestrated startup is a
separate managed-launch boundary: durable prompt file, explicit runtime/loadout,
visible desktop proof when requested, watcher, closeout, and reportback.

For managed Claude Code launches, the launch adapter also pins the model at process start. The current default is `claude-fable-5`, emitted as `claude --model claude-fable-5`. This avoids inheriting stale Claude Code TUI/default model state. Short display aliases like `fable` or product-family names like `mythos` are not treated as reliable launch IDs unless verified in your environment. Override the default with `HERMES_CLAUDE_MODEL` (or `CLAUDE_CODE_MODEL`) for Claude and `HERMES_CODEX_MODEL` (or `CODEX_MODEL`) for Codex.

Keep adapter parity and launch parity separate. A loadout can materialize cleanly
for Claude and Codex while a wrapper still launches one runtime incorrectly. Use
[Managed Visible Launch Contract](../guides/managed-visible-launch-contract.md)
for startup proof.

## Safety boundary

Materialization writes generated files and a manifest. It must never touch
runtime authentication state, session databases, or unrelated plugin state
in a live runtime home. Sandbox output (`--output-root output`) is the
default posture; see
[Live Home vs Output Mode](../guides/live-home-vs-output-mode.md) before writing
into a real runtime home.

## Related documentation

- **Explanation:** [Routing Model](routing-model.md),
  [Hermes Skill Control Plane](hermes-skill-control-plane.md),
  [Loadout Inheritance](loadout-inheritance.md)
- **Tutorial:** [Prepare Claude and Codex](../tutorials/prepare-claude-and-codex.md)
- **How-to:** [Live Home vs Output Mode](../guides/live-home-vs-output-mode.md)
