# Tutorial: Your first loadout run

Goal: go from a fresh checkout to a generated Claude research loadout in sandbox
output. This tutorial does not write into a live Claude or Codex home.

Time: about five minutes.

## 1. Clone the repo

```bash
git clone <public-repo-url> <GITHUB_REPO_NAME>
cd <GITHUB_REPO_NAME>
```

If the repo is already present:

```bash
git status --short --branch
```

Continue only if you are not about to overwrite local work.

## 2. Validate the loadout repo

```bash
python scripts/validate_loadouts.py
```

Expected:

```text
loadouts valid
```

This confirms the manifests, inheritance, runtime maps, and shared surfaces are
structurally coherent enough to materialize.

## 3. Resolve an explicit loadout

For a first run, choose the loadout explicitly:

```bash
python scripts/resolve_route.py \
  --runtime claude \
  --request "Use Claude for research" \
  --explicit-loadout research
```

Expected:

```text
research
```

The request text is preserved for operator context; `--explicit-loadout` removes
ambiguity for the tutorial.

## 4. Materialize a sandbox output

```bash
python scripts/apply_loadout.py \
  --runtime claude \
  --loadout research \
  --output-root output
```

This writes the generated Claude surface under `output/claude/`.

## 5. Inspect the generated files

```bash
find output/claude -maxdepth 2 -type f | sort | sed -n '1,40p'
```

You should see a runtime-shaped surface with files such as:

```text
output/claude/CLAUDE.md
output/claude/commands/...
output/claude/rules/...
output/claude/skills/...
output/claude/hermes-loadout.json
```

Now inspect the manifest:

```bash
python - <<'PY'
import json
from pathlib import Path
manifest = json.loads(Path('output/claude/hermes-loadout.json').read_text())
print('runtime:', manifest['runtime'])
print('loadout:', manifest['loadout'])
print('resolved_from:', ' -> '.join(manifest['resolved_from']))
print('managed_files:', len(manifest.get('managed_files', [])))
PY
```

Expected first lines:

```text
runtime: claude
loadout: research
resolved_from: default -> research
```

## 6. Try Codex sandbox output

```bash
python scripts/apply_loadout.py \
  --runtime codex \
  --loadout research \
  --output-root output
```

Inspect `output/codex/hermes-loadout.json` the same way. The shared loadout
intent should be recognizable, but the generated files should be Codex-shaped.

## 7. Clean up

```bash
rm -rf output/
```

You have not touched a live runtime home. The run is fully reversible.

## What you learned

- A runtime is the agent CLI (`claude` or `codex`).
- A loadout is the behavior surface layered onto the baseline.
- Sandbox materialization lets you inspect generated files before live use.
- `hermes-loadout.json` is the generated manifest that proves what was selected
  and written.

Next: read [`../architecture/README.md`](../architecture/README.md) to understand
how baselines, overlays, shared surfaces, and runtime adapters fit together.
