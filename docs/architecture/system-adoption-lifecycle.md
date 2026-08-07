# System adoption lifecycle

System adoption is the process of turning another repo, skill pack, hook pack, prompt library, or runtime setup into reviewed loadout behavior for Claude Code and Codex. The lifecycle keeps source review, loadout design, sandbox output, and live adoption separate so a useful idea can be adopted without copying private state or bloating the default surface.

```text
source system
     │
     ▼
review ledger ── evidence, files, commands, risks
     │
     ▼
candidate loadout design ── shared intent + runtime-specific expression
     │
     ▼
sandbox materialization ── output/claude + output/codex
     │
     ▼
approval gate ── operator reviews evidence and generated surfaces
     │
     ▼
live adoption ── merge loadout changes or apply to a real runtime home
```

## Stage 1 — source system

A source system can be a project repo, an existing agent configuration, a command library, a skill pack, a hook pack, or a prompt pack. Treat it as evidence, not as code to copy blindly.

Inventory:

- what the source does;
- which commands it exposes;
- which files are policy, prompts, scripts, hooks, or runtime config;
- which parts are private, machine-specific, or credential-bearing;
- what behavior should become reusable agent posture.

## Stage 2 — review ledger

The review ledger is the adoption notes layer. It records what was inspected and what should happen next. It should include enough evidence for another agent or human to reproduce the decision.

A review ledger should answer:

- Which source files were read?
- Which behavior belongs in a shared loadout?
- Which behavior belongs only in a runtime adapter?
- Which behavior should stay out of this system?
- Which commands prove the candidate is safe?

## Stage 3 — candidate loadout design

Candidate design converts the source idea into this repo's model.

Use `shared/` for behavior that should be runtime-neutral: task posture, checklists, safety rules, and reusable instructions.

Use `loadouts/<name>/loadout.yaml` for named mode selection: aliases, routing hints, purpose, session policy, inherited base, and included packs.

Use `adapters/<runtime>/` only when Claude Code and Codex need different file shapes for the same behavior.

Keep `default` lean. Put specialty behavior in a named loadout unless every ordinary coding session should receive it.

## Stage 4 — sandbox materialization

A candidate is not adopted just because files were edited. It becomes reviewable when it materializes into a sandbox surface.

```bash
python scripts/validate_loadouts.py
rm -rf output
python scripts/apply_loadout.py --runtime claude --loadout <candidate> --output-root output
python scripts/apply_loadout.py --runtime codex --loadout <candidate> --output-root output
```

Inspect:

- `output/claude/hermes-loadout.json`;
- `output/codex/hermes-loadout.json`;
- the generated Claude-specific files;
- the generated Codex-specific files;
- whether both runtimes express the same operator-facing behavior.

## Stage 5 — approval gate

Approval is the boundary between a candidate and adopted behavior. The gate exists because source systems often contain assumptions that are valid only for one operator, one machine, or one runtime.

Before approval, the handoff should include:

- the intended loadout name;
- files changed;
- source evidence;
- validation output;
- sandbox manifest summaries;
- known limitations;
- explicit confirmation that no live-home write occurred unless requested.

## Stage 6 — live adoption

Live adoption means either merging the reviewed repo changes or materializing the approved loadout into an actual runtime home. Keep those two operations distinct.

Repo adoption is verified with:

```bash
python scripts/validate_loadouts.py
git diff --check
```

Live-home adoption happens only after sandbox review and operator approval. See [Live Home vs Output Mode](../guides/live-home-vs-output-mode.md).

## Relationship to existing architecture

- [Routing Model](routing-model.md) explains how a request chooses a loadout.
- [Loadout Inheritance](loadout-inheritance.md) explains why `default` stays lean.
- [Runtime Adapters](runtime-adapters.md) explains why Claude and Codex receive different file shapes.
- [Onboard a system into agents](../tutorials/onboard-a-system-into-agents.md) shows the lifecycle as an executable tutorial.
