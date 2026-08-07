> `docs/guides/live-home-vs-output-mode.md`. Remove this notice when
> promoting.

# Live Home vs Output Mode

`apply_loadout.py` can materialize a loadout into two very different places.
Understand the difference before your first live apply.

Live-home materialization and live runtime launch are separate approval gates.
Writing files into a runtime home changes what a future CLI launch sees; launching
Claude Code or Codex starts an authenticated process now.

| | Output mode (sandbox) | Live-home mode |
| --- | --- | --- |
| Writes to | `output/<runtime>/` inside the repo | the real runtime home (e.g. `~/.claude`, `~/.codex`) |
| Read by a real agent | never | yes, on next launch |
| Risk | none — inspect and delete | medium — changes live agent behavior |
| Undo | `rm -rf output/` | restore the pre-apply backup |
| When | always first; every change; every experiment | only after the same loadout was reviewed in sandbox |

## Output mode — the default posture

```bash
python scripts/apply_loadout.py \
  --runtime claude \
  --loadout writing-docs \
  --output-root output
```

Inspect what was generated before anything real reads it:

```bash
find output/claude -maxdepth 2 -type f | sort | sed -n '1,40p'
```

You should see a runtime-shaped surface (`CLAUDE.md`, `commands/`, `rules/`,
`skills/`, `hermes-loadout.json`). Undo is total and trivial:

```bash
rm -rf output/
```

## Live-home mode — deliberate, reviewed, reversible

Live-home mode writes the same surface into the directory your real `claude`
or `codex` CLI reads at launch. Three rules:

1. **Sandbox first, always.** Materialize the exact runtime/loadout pair
   into `output/` and review it before any live apply.
2. **Back up before writing.** Copy the target home aside so rollback is a
   rename, not an archaeology project.
3. **Verify after writing.** Read the manifest in the live home and confirm
   it names the runtime and loadout you intended.

```bash
# 1. Review in sandbox
python scripts/apply_loadout.py --runtime claude --loadout writing-docs --output-root output

# 2. Back up the live home
cp -a ~/.claude ~/.claude.backup-before-loadout

# 3. Apply live
python scripts/apply_loadout.py \
  --runtime claude \
  --loadout writing-docs \
  --output-root ~/.claude --target-home

# 4. Verify what is now active
python - <<'PY'
import json, os
from pathlib import Path
m = json.loads((Path(os.path.expanduser("~/.claude")) / "hermes-loadout.json").read_text())
print(m["runtime"], m["loadout"])
PY
```

You should see:

```text
claude writing-docs
```

Runtime homes differ by operator and platform — do not guess paths for
someone else's machine. If an orchestrator or wrapper manages the launch,
let it supply the target home.

## Live launch after live apply

If the operator approves an actual Claude Code/Codex launch, use the managed
visible launch contract. Do not start raw `claude`, raw `codex`, or ad-hoc tmux
as the normal path. The launch proof must include a durable prompt file, manifest,
watcher/closeout state, and desktop-window proof when visibility was requested.

See [Managed Visible Launch Contract](managed-visible-launch-contract.md).

## What live apply must never touch

Materialization manages its own generated files (tracked in the manifest's
`managed_files`). It must never overwrite:

- runtime authentication or credential state,
- session history or session databases,
- unrelated plugins, caches, or personal configuration.

If a live apply would collide with something it does not manage, stop and
review rather than forcing it.

## Rollback

```bash
rm -rf ~/.claude
mv ~/.claude.backup-before-loadout ~/.claude
```

Then launch the runtime once and confirm it behaves as before. Keep the
backup until you have verified the new surface across at least one real
session.

## Related documentation

- **Explanation:** [Runtime Adapters](../architecture/runtime-adapters.md)
- **How-to:** [Choosing a Loadout](choosing-a-loadout.md)
- **Tutorial:** [Prepare Claude and Codex](../tutorials/prepare-claude-and-codex.md)
