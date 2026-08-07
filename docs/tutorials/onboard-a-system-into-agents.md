# Onboard a system into agents

This tutorial walks through a sandbox-only adoption exercise. You will treat an existing loadout as the source system, create review evidence, materialize Claude and Codex surfaces, and stop before live adoption.

The example uses the built-in `writing-docs` loadout because it is safe, portable, and already present in a clean clone.

## Step 1 — start clean

```bash
git status --short --branch
python scripts/validate_loadouts.py
```

Expected validation output:

```text
loadouts valid
```

## Step 2 — inventory the source behavior

```bash
python - <<'PY'
import yaml
from pathlib import Path
p = Path('loadouts/writing-docs/loadout.yaml')
data = yaml.safe_load(p.read_text())
print(data['name'])
print(data['purpose'])
print('packs:', ', '.join(data.get('packs', [])))
print('supports:', ', '.join(data.get('supported_runtimes', [])))
PY
```

Expected first line:

```text
writing-docs
```

Classify the source:

- shared intent: documentation posture and verification expectations;
- runtime adapter material: only file-shape differences handled by adapters;
- not adopted: private operator-specific routes, IDs, paths, or credentials.

## Step 3 — write a temporary review ledger

Use a temp file outside the repo so the tutorial leaves no committed adoption artifact:

```bash
cat > /tmp/terminal-loadout-adoption-ledger.md <<'EOF'
# Adoption ledger: writing-docs example

Source: loadouts/writing-docs/loadout.yaml
Decision: use as a safe fixture for proving adoption review mechanics.
Shared behavior: documentation planning, editing, verification, and handoff.
Runtime adapter changes: none for this tutorial.
Live-home adoption: not approved; sandbox only.
EOF
```

## Step 4 — materialize Claude and Codex sandbox outputs

```bash
rm -rf output
python scripts/apply_loadout.py --runtime claude --loadout writing-docs --output-root output
python scripts/apply_loadout.py --runtime codex --loadout writing-docs --output-root output
```

Expected: both commands succeed and create manifest files.

## Step 5 — compare generated manifests

```bash
python - <<'PY'
import json
from pathlib import Path
for runtime in ('claude', 'codex'):
    m = json.loads(Path(f'output/{runtime}/hermes-loadout.json').read_text())
    print(runtime)
    print('  loadout:', m['loadout'])
    print('  chain:', ' -> '.join(m['resolved_from']))
    print('  managed files:', len(m.get('managed_files', [])))
PY
```

Expected: both runtimes report `writing-docs`, and both chains include `default -> writing-docs`.

## Step 6 — inspect the generated surfaces

```bash
find output/claude -maxdepth 2 -type f | sort | sed -n '1,30p'
find output/codex -maxdepth 2 -type f | sort | sed -n '1,30p'
```

The file names differ because the runtimes expect different surfaces. The behavior should still be equivalent: both should know they are running the documentation-focused loadout.

## Step 7 — run the public safety gates

```bash
git diff --check
```

Expected highlights:

```text
public_docs_safe: ... copied-file candidates checked
public_copy_safe: ... files extracted and verified
```

## Step 8 — stop at the approval gate

Do not apply to a live home in this tutorial. A real adoption handoff should include:

- source system reviewed;
- intended shared behavior;
- runtime-specific changes, if any;
- validation output;
- Claude/Codex manifest summaries;
- approval status.

Delete tutorial scratch output when finished:

```bash
rm -rf output /tmp/terminal-loadout-adoption-ledger.md
```

## What to change for a real source system

For a real external source, replace Step 2 with a source inventory and write the ledger under a reviewable path chosen by the operator. Keep the same boundary: source review first, candidate design second, sandbox materialization third, approval before live adoption.

For the conceptual model, see [System Adoption Lifecycle](../architecture/system-adoption-lifecycle.md).
