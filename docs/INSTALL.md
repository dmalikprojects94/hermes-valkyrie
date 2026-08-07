# Install

Three install paths. Start with sandbox output unless you already understand the
runtime-home risk.

## 1. Inspect-only

Use this when you want to understand the repo without generating runtime files.

```bash
git clone <public-repo-url> <GITHUB_REPO_NAME>
cd <GITHUB_REPO_NAME>
python -m pip install pyyaml
python scripts/validate_loadouts.py
```

Expected:

```text
loadouts valid
```

Risk: none beyond reading the repo and running validation.

## 2. Sandbox materialization — recommended first run

Use this to generate a runtime surface into `output/` so you can inspect it
before touching a live agent home.

```bash
python scripts/apply_loadout.py \
  --runtime claude \
  --loadout research \
  --output-root output
```

Inspect:

```bash
find output/claude -maxdepth 2 -type f | sort | sed -n '1,40p'
python - <<'PY'
import json
from pathlib import Path
m = json.loads(Path('output/claude/hermes-loadout.json').read_text())
print(m['runtime'], m['loadout'])
PY
```

Risk: low. Delete `output/` to undo.

## 3. Live runtime home — advanced

Use this only after sandbox output has been reviewed. Live-home materialization
writes files that the real `claude` or `codex` CLI may read on launch.

Before live-home mode:

```bash
python scripts/validate_loadouts.py
python scripts/apply_loadout.py --runtime claude --loadout research --output-root output
```

Then use `scripts/apply_live_system.py` (read its `--help` first) or your
orchestrator's wrapper to move reviewed output into a live home. Do not guess at
`~/.claude`, `~/.codex`, or a custom `HOME` override; runtime homes differ by
operator and platform.

Risk: medium. Back up the target runtime home first and keep a rollback path.

## Verifying a change

After editing loadouts, adapters, or shared surfaces:

```bash
python scripts/validate_loadouts.py
git diff --check
python scripts/apply_loadout.py --runtime claude --loadout research --output-root output
python scripts/apply_loadout.py --runtime codex --loadout research --output-root output
```

Substitute the affected loadout(s) for `research`.

## Uninstall / cleanup

Sandbox cleanup:

```bash
rm -rf output/
```

Live-home cleanup depends on the target runtime and how it was applied. Prefer
restoring from the backup made before live-home materialization.
