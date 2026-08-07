# Tutorial: Add a New Loadout

Goal: author a new specialty loadout on top of the `default` backbone,
validate it, materialize it for both runtimes in sandbox output, and prove
the inheritance chain carried the backbone through. Everything stays in
sandbox — no live runtime home is touched.

Time: about ten minutes.

## Prerequisites

| Requirement | Check |
| --- | --- |
| Repo cloned and validating | `python scripts/validate_loadouts.py` → `loadouts valid` |
| Python 3 on PATH | `python --version` |

## 1. Create the loadout directory

We'll add a `data-analysis` loadout as the worked example. It is small enough to inspect in one sitting and concrete enough to show routing, inheritance, and dual-runtime materialization.

```bash
mkdir -p loadouts/data-analysis
```

## 2. Write `loadout.yaml`

```bash
cat > loadouts/data-analysis/loadout.yaml <<'YAML'
name: data-analysis
description: Dataset exploration, metrics work, and analysis notebooks.
base: default
aliases: [data-analysis, data analysis, analytics]
supported_runtimes: [claude, codex]
routing:
  default: false
  priority: 60
  explicit_keywords:
    - data analysis
    - analyze the dataset
    - metrics deep dive
purpose: Keep dataset work evidence-first with explicit verification of every claim.
when_to_use:
  - Exploring a dataset or metrics question before drawing conclusions.
when_not_to_use:
  - Ordinary feature work that happens to read a CSV.
shared_instructions:
  - core-operating-rules
  - reporting-contract
shared_skills:
  - verification-loop
packs: []
session_policy:
  prefer_fresh_session: true
  compact_warning_band: 35-55%
  reuse_allowed: true
runtime_overrides:
  claude:
    commands: []
    agents: []
    hooks: []
    mcp: []
  codex:
    config:
      approval_policy: on-request
      sandbox_mode: workspace-write
YAML
```

The load-bearing lines:

- `base: default` — inherit the backbone instead of restating it.
- `aliases` + `routing.explicit_keywords` — reviewable routing vocabulary for callers and orchestrators. The resolver is sticky-default unless the caller passes `--explicit-loadout` or the request explicitly says it wants this loadout.
- `shared_instructions` / `shared_skills` — names of shared surfaces this
  loadout adds. Inheritance dedup-unions them with everything `default`
  already carries.

## 3. Validate

```bash
python scripts/validate_loadouts.py
```

You should see:

```text
loadouts valid
```

If validation fails, read the message — it names the offending loadout and
field (unknown base, unknown shared skill, structural problem). Fix before
continuing.

## 4. Confirm the route resolves

```bash
python scripts/resolve_route.py \
  --runtime claude \
  --request "Use Claude with the data-analysis loadout for last month's numbers"
```

You should see:

```text
data-analysis
```

## 5. Materialize both runtimes into sandbox

```bash
python scripts/apply_loadout.py --runtime claude --loadout data-analysis --output-root output
python scripts/apply_loadout.py --runtime codex  --loadout data-analysis --output-root output
```

## 6. Prove inheritance carried the backbone

```bash
python - <<'PY'
import json
from pathlib import Path
for runtime in ("claude", "codex"):
    m = json.loads(Path(f"output/{runtime}/hermes-loadout.json").read_text())
    print(runtime, "|", " -> ".join(m["resolved_from"]), "|",
          len(m.get("managed_files", [])), "managed files")
PY
```

You should see both manifests carry the parent-first chain:

```text
claude | default -> data-analysis | <N> managed files
codex | default -> data-analysis | <M> managed files
```

Spot-check that a backbone surface you did not declare is present — that is
inheritance working:

```bash
ls output/claude/skills/ | head
```

## 7. Clean up

```bash
rm -rf output/
```

To remove the experiment entirely:

```bash
rm -rf loadouts/data-analysis
python scripts/validate_loadouts.py
```

You should see `loadouts valid` again.

## What you learned

- A loadout is one directory with one `loadout.yaml`; `base:` does the
  heavy lifting.
- Routing is declared, deterministic, and testable before any launch.
- The manifest's `resolved_from` chain is the proof of what layered onto
  what — verify at the child, and check both runtimes.

## Related documentation

- **Explanation:** [Loadout Inheritance](../architecture/loadout-inheritance.md)
- **How-to:** [Choosing a Loadout](../guides/choosing-a-loadout.md)
- **Tutorial:** [Prepare Claude and Codex](prepare-claude-and-codex.md)
