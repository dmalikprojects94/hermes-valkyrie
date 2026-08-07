> `docs/tutorials/prepare-codex-and-claude.md`. Remove this notice when
> promoting.

# Tutorial: Prepare Claude and Codex from One Loadout

Goal: materialize the same loadout for both runtimes, compare the two
generated surfaces, and learn how to read a parity gap honestly. Everything
stays in sandbox output.

Time: about ten minutes.

## Prerequisites

| Requirement | Check |
| --- | --- |
| Repo cloned and validating | `python scripts/validate_loadouts.py` → `loadouts valid` |
| Python 3 on PATH | `python --version` |
| (Optional, live use only) `claude` / `codex` CLIs authenticated | not needed for this tutorial |

Neither runtime CLI needs to be installed to run this tutorial — you are
generating and inspecting files, not launching agents.

## 1. Pick a dual-runtime loadout

Any loadout with `supported_runtimes: [claude, codex]` works. We'll use
`research`.

```bash
python scripts/validate_loadouts.py
```

You should see:

```text
loadouts valid
```

## 2. Materialize both surfaces

```bash
python scripts/apply_loadout.py --runtime claude --loadout research --output-root output
python scripts/apply_loadout.py --runtime codex  --loadout research --output-root output
```

## 3. Compare the shapes

```bash
find output/claude -maxdepth 1 | sort
echo ---
find output/codex -maxdepth 1 | sort
```

You should see two differently shaped surfaces for the same intent —
roughly:

```text
output/claude/CLAUDE.md
output/claude/agents
output/claude/commands
output/claude/rules
output/claude/skills
output/claude/hermes-loadout.json
---
output/codex/config.toml
output/codex/memories
output/codex/skills
output/codex/hermes-loadout.json
```

This asymmetry is the design, not a bug: shared intent, runtime-specific
expression. Claude gets slash commands, subagents, and rules files; Codex
gets skills, a managed memory note, and a managed `config.toml` block.

## 4. Confirm both manifests agree on the intent

```bash
python - <<'PY'
import json
from pathlib import Path
for runtime in ("claude", "codex"):
    m = json.loads(Path(f"output/{runtime}/hermes-loadout.json").read_text())
    print(runtime, m["loadout"], "->", " -> ".join(m["resolved_from"]))
PY
```

You should see:

```text
claude research -> default -> research
codex research -> default -> research
```

## 5. Compare command surfaces

```bash
python scripts/list_runtime_commands.py --runtime claude --loadout research
python scripts/list_runtime_commands.py --runtime codex  --loadout research
```

Claude lists native slash commands; Codex lists command-equivalent surfaces.
Where a Claude command has no Codex equivalent, that is a **documented
parity gap**, classified as one of: `synced`, `shared-only`,
`claude-only-acceptable`, `codex-only-acceptable`, `missing-claude`,
`missing-codex`, or `intentional-gap`.

The failure rule worth internalizing: never call a loadout synchronized
just because both runtimes accept its name. Synchronized means the behavior
you rely on has an equivalent surface on both sides — or a written reason
why not.

## 6. Clean up

```bash
rm -rf output/
```

## Going live (out of scope here)

Launching a real agent against these surfaces requires an authenticated
`claude` or `codex` CLI and a live-home apply. That path, its risk profile,
and its rollback are covered in
[Live Home vs Output Mode](../guides/live-home-vs-output-mode.md).

## What you learned

- One loadout definition drives both runtimes; adapters shape the output.
- The two generated surfaces are intentionally different in form and
  intentionally equivalent in behavior.
- Parity is a tracked claim with a vocabulary, not an assumption.

## Related documentation

- **Explanation:** [Runtime Adapters](../architecture/runtime-adapters.md)
- **How-to:** [Live Home vs Output Mode](../guides/live-home-vs-output-mode.md)
- **Tutorial:** [Add a New Loadout](add-a-new-loadout.md)
