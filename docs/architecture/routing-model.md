# Routing Model

Every run of the Terminal Loadout System starts with two routing decisions and,
when an agent will actually be launched, one launch-mode decision:

1. **Runtime** — which agent CLI executes the work: `claude` or `codex`.
2. **Loadout** — which named behavior surface that runtime launches with.
3. **Launch mode** — inspect-only, sandbox materialization, managed visible launch, or CI/non-interactive launch.

Keeping the decisions separate is the core design commitment. The runtime
answers "which terminal?" The loadout answers "which posture?" Launch mode
answers "are we only preparing files, launching visibly for an operator, or
running non-interactively?" Any loadout that supports both runtimes can be
materialized for either without editing the loadout itself.

```text
        operator request
              │
              ▼
   ┌─────────────────────┐
   │  1. pick runtime    │   claude | codex
   │  (caller decides;   │
   │   never inferred    │
   │   by this repo)     │
   └─────────┬───────────┘
             │
             ▼
   ┌─────────────────────┐
   │  2. resolve loadout │
   │                     │
   │  explicit name? ────┼── yes ──▶ use it
   │        │            │
   │        no           │
   │        ▼            │
   │  alias/keyword      │
   │  match in request? ─┼── yes ──▶ matched loadout
   │        │            │
   │        no           │
   │        ▼            │
   │      default        │
   └─────────┬───────────┘
             │
             ▼
   (runtime, loadout) pair → materialization
```

## Who makes each decision

The repo deliberately does not choose a runtime. The caller — a human, a
script, or your orchestrator — picks `claude` or `codex` first, then hands
the request text to loadout resolution. This keeps the loadout layer free of
runtime-preference policy.

Loadout resolution has three tiers, strongest first:

1. **Explicit CLI selection.** The caller passes `--explicit-loadout`. Always wins.
2. **Explicit operator phrasing.** Request text can name the loadout in an explicit pattern such as `with research`, `using the writing-docs loadout`, or `via deep-coding`.
3. **Fallback to `default`.** Ordinary task words like "research", "planning", or "documentation" describe the work; they do not silently switch loadouts.

## Resolving a route

Explicit selection:

```bash
python scripts/resolve_route.py \
  --runtime claude \
  --request "Use Claude for research" \
  --explicit-loadout research
```

You should see:

```text
research
```

Explicit phrasing inside request text:

```bash
python scripts/resolve_route.py \
  --runtime claude \
  --request "Use Claude with the writing-docs loadout to write the runbook"
```

You should see:

```text
writing-docs
```

Ordinary task words without an explicit loadout stay on the sticky default:

```bash
python scripts/resolve_route.py \
  --runtime claude \
  --request "Write the runbook and API documentation for this service"
```

You should see:

```text
default
```

## Deterministic on purpose

Routing is deterministic explicit selection, not semantic intent detection.
A request that does not explicitly name a loadout lands on `default` — a safe,
predictable outcome — rather than on a model's best guess. This makes routes
testable: the same request text always resolves to the same loadout, and a
new alias or explicit phrase is a reviewable diff in a `loadout.yaml`.

If you need smarter intent detection, put it in the caller: resolve the
loadout name however you like, then pass it with `--explicit-loadout`.

## Launch mode is explicit

After runtime/loadout resolution, do not assume that materialization means live
launch. Use these modes deliberately:

| Mode | Meaning | Approval posture |
| --- | --- | --- |
| Inspect-only | Read docs, validate, and inspect route decisions. | Safe default. |
| Sandbox materialization | Write generated runtime files under `output/`. | Safe default. |
| Managed visible launch | Launch Claude/Codex through `run_loaded_agent.py` and prove desktop-window visibility. | Requires operator approval for authenticated runtime use. |
| CI/non-interactive launch | Bounded automation where no human needs to watch a desktop terminal. | Must be labeled as non-interactive. |

For managed visible launch, follow [Managed Visible Launch Contract](../guides/managed-visible-launch-contract.md).

## What happens after resolution

The `(runtime, loadout)` pair feeds materialization:

```bash
python scripts/apply_loadout.py \
  --runtime claude \
  --loadout research \
  --output-root output
```

The generated surface lands under `output/claude/` with a
`hermes-loadout.json` manifest recording exactly which runtime, loadout, and
inheritance chain produced it. How that surface is shaped per runtime is the
subject of [Runtime Adapters](runtime-adapters.md); how loadouts
layer onto the baseline is the subject of
[Loadout Inheritance](loadout-inheritance.md).

## Related documentation

- **Explanation:** [Runtime Adapters](runtime-adapters.md),
  [Loadout Inheritance](loadout-inheritance.md)
- **How-to:** [Choosing a Loadout](../guides/choosing-a-loadout.md)
- **Tutorial:** ../tutorials/first-loadout-run.md (shipped in `docs/tutorials/`)
