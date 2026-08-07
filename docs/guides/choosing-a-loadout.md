# Choosing a Loadout

A loadout is an operating mode, not a theme. Pick the one whose posture the
task actually benefits from; when in doubt, `default` is always safe.

## Quick decision tree

```text
  "What kind of work is this?"
        │
        ├─ mixed / routine / unsure ──────────────▶ default
        │
        ├─ implementation work
        │     ├─ moderate feature / bugfix ───────▶ coding
        │     └─ long multi-file build, refactor,
        │        architecture-sensitive ──────────▶ deep-coding
        │
        ├─ investigation before action ───────────▶ research
        ├─ scoping, PRDs, sequencing, handoffs ───▶ project-planner
        ├─ deploy / CI / hosting / rollback ──────▶ devops
        ├─ READMEs, runbooks, API docs ───────────▶ writing-docs
        │
        ├─ UI work
        │     ├─ browser-verified implementation ─▶ frontend-design
        │     ├─ competitor / reference audit ────▶ frontend-research-audit
        │     └─ artifact-first prototypes ───────▶ open-design
        │
        ├─ marketing / conversion copy ───────────▶ marketing
        ├─ animation, video, render work ─────────▶ media-video
        └─ maintaining this system itself ────────▶ loadout-management
```

## The catalog

| Loadout | Use it for | Don't use it for |
| --- | --- | --- |
| `default` | Routine coding, review, triage, light planning. The lean backbone every other loadout inherits. | Anything that clearly benefits from a specialty below. |
| `coding` | Moderate features, local refactors, focused debugging, TDD-lite loops. | Deep planning or long architecture programs — go up a tier. |
| `deep-coding` | Sustained multi-file builds with stronger phase discipline, context hygiene, heavier verification. | Quick fixes; the ceremony isn't worth it. |
| `research` | Evidence-backed investigation, source separation, synthesis before action. | Tasks where the answer is already known and just needs implementing. |
| `project-planner` | Scoping, sequencing, issue breakdown, handoff-ready plans. | Executing the plan — hand off to a coding loadout. |
| `devops` | Deployment, CI/CD, observability, rollout/rollback work. | Application feature work that merely touches a config file. |
| `writing-docs` | User docs, runbooks, API docs, changelogs, durable handoffs. | Code changes where docs are a closeout note. |
| `frontend-design` | Browser-verified UI implementation and visual QA. | Backend work with an incidental template edit. |
| `frontend-research-audit` | Reference-site and competitor UI audits. | Building the UI — that's `frontend-design`. |
| `open-design` | Artifact-first prototypes, mockups, visual concepts. | Production UI wiring. |
| `marketing` | Conversion copy, positioning, campaign material. | Technical documentation — that's `writing-docs`. |
| `media-video` | Animation, video, render pipelines. | General coding. |
| `loadout-management` | Auditing and maintaining the loadout system itself. | Normal project work. |

## Verify your choice before launching

Resolution is deterministic, so you can test explicit phrasing before launch:

```bash
python scripts/resolve_route.py \
  --runtime claude \
  --request "Use Claude with the frontend-research-audit loadout for a competitor onboarding flow audit"
```

You should see:

```text
frontend-research-audit
```

If the resolver lands on `default` when you expected a specialty, name the
loadout explicitly with `--explicit-loadout` or use a request phrase like
`with <loadout> loadout`. Do not rely on ordinary task keywords to switch
modes; the default is intentionally sticky.

## Rules of thumb

- **Start lean.** `default` inheriting into everything means a specialty
  loadout is never *less* capable than default — but specialty context costs
  attention. Only pay for posture the task uses.
- **One mode per session.** Prefer a fresh session when the work changes
  mode (say, planning → deep implementation) instead of dragging one bloated
  context across modes.
- **Explicit beats inferred.** Automation and orchestrators should pass
  `--explicit-loadout` whenever the mode is already known.

## Related documentation

- **Explanation:** [Routing Model](../architecture/routing-model.md),
  [Loadout Inheritance](../architecture/loadout-inheritance.md)
- **How-to:** [Live Home vs Output Mode](live-home-vs-output-mode.md)
- **Tutorial:** [Add a New Loadout](../tutorials/add-a-new-loadout.md)
