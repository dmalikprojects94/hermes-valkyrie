> `docs/architecture/loadout-inheritance.md`. Remove this notice when
> promoting.

# Loadout Inheritance

Loadouts layer. A lean `default` backbone carries the posture every run
needs; named loadouts extend it — or extend each other — via a `base:` field
in `loadout.yaml`. Inheritance is what keeps the baseline small: specialty
behavior is declared once in a parent and flows to every child.

```text
                    default  (backbone, base: null)
                       │
     ┌─────────┬───────┼────────────┬─────────────┐
     ▼         ▼       ▼            ▼             ▼
 deep-coding  research  writing-docs  devops   frontend-design
                                                  │
                                       ┌──────────┴──────────┐
                                       ▼                     ▼
                            frontend-research-audit     open-design
```

A three-deep chain like `open-design → frontend-design → default` resolves
parent-first: `default` first, then `frontend-design` merged onto it, then
`open-design` merged onto that.

## Merge rules

When a child merges onto its resolved parent, every field follows one of
three rules:

- **Lists → dedup-union, parent-first order.** Every parent item is kept in
  order, then child items not already present are appended. Parent
  `shared_skills: [a, b]` + child `shared_skills: [b, c]` → `[a, b, c]`.
  Applies to `shared_instructions`, `shared_skills`, `packs`, and the
  per-runtime command/agent/hook/MCP lists.
- **Dicts → deep-merge.** Parent-only keys are kept, child-only keys are
  added, shared keys recurse. Applies to `runtime_overrides` and its nested
  per-runtime `config` blocks.
- **Scalars → child override.** Any non-list/non-dict value (or a
  parent/child type mismatch) resolves to the child's value.

## A child never inherits its parent's identity

After the merge, these fields are always the child's own, so extending a
parent can never hijack its name or routing:

- `name`, `description`, `purpose`, `when_to_use`, `when_not_to_use`
- `aliases` — the child's list only
- `routing` — the child's routing block **replaces** the parent's outright;
  routing is never merged
- `supported_runtimes` — the child's if declared, else inherited

One exception by design: `session_policy` is deep-merged, so a child can
tune a single session knob without restating the whole block.

## Provenance: `resolved_from`

Every resolved loadout carries its full parent-first chain, and the chain is
written into the materialized manifest:

```bash
python scripts/apply_loadout.py --runtime claude --loadout research --output-root output
python - <<'PY'
import json
from pathlib import Path
m = json.loads(Path("output/claude/hermes-loadout.json").read_text())
print(" -> ".join(m["resolved_from"]))
PY
```

You should see:

```text
default -> research
```

Materialization consumes the same chain: runtime surface directories are
copied in `resolved_from` order, so a child's files can override a parent's
where they collide, and any caller can reconstruct which layer contributed
what.

## Failure modes are loud

- **Unknown loadout or unknown `base:`** — resolution fails immediately;
  validation reports the unknown base by name.
- **Circular inheritance** — a `base:` cycle is detected and rejected with
  an explicit error before any infinite descent.

```bash
python scripts/validate_loadouts.py
```

You should see:

```text
loadouts valid
```

## Why this matters in practice

Patching a **parent** loadout's `shared_skills` propagates the new entry to
every child automatically — no child file is edited. The flip side: when you
change a parent, verify at a **child** materialization, not just the parent.
The child surface actually containing the inherited skill is the proof that
inheritance carried it:

```bash
python scripts/apply_loadout.py --runtime claude --loadout open-design --output-root output
ls output/claude/skills/
```

You should see the parent-contributed skills alongside the child's own.

## Related documentation

- **Explanation:** [Routing Model](routing-model.md),
  [Runtime Adapters](runtime-adapters.md)
- **Tutorial:** [Add a New Loadout](../tutorials/add-a-new-loadout.md)
- **How-to:** [Choosing a Loadout](../guides/choosing-a-loadout.md)
