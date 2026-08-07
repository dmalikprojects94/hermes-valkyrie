# Public product repo shape

This is the target shape for a clean, shareable Terminal Loadout System release.
The public repo is a product repo, not a dump of private development history.

## Top-level folders

```text
terminal-loadout-system/
├── README.md
├── LICENSE
├── CHANGELOG.md
├── .env.example
├── .gitignore
├── config/
├── docs/            (includes SECURITY.md and CONTRIBUTING.md)
├── scripts/
├── loadouts/
├── shared/
├── adapters/
├── examples/
└── .github/
```

## What belongs where

### Root files

Root files are the public front door and governance layer.

- `README.md` explains the product, audience, quickstart, and release status.
- `LICENSE` defines reuse terms.
- `SECURITY.md` defines secret handling and vulnerability reporting.
- `CONTRIBUTING.md` defines contribution and validation rules.
- `.env.example` stays placeholder-only.
- `.gitignore` keeps local runtime homes, `.env`, generated output, and caches out of source.

### `config/`

Public configuration templates only.

```text
config/
└── onboarding.example.toml
```

Real operator answers belong in untracked local files, environment variables, or gateway metadata.

### `docs/`

Public documentation only: install, quickstart, architecture, guides, integrations, reference, troubleshooting, and product governance.

No private plans, dated run logs, operator-specific audits, private chat IDs, or live environment notes belong here.

### `scripts/`

Only product scripts that are documented, tested, and portable in a fresh clone.

If a public doc references `scripts/<name>.py`, that file and its dependency closure must ship in the public repo. The maintainer release gate enforces this.

### `loadouts/`

The product payload: named behavior surfaces such as `default`, `coding`, `deep-coding`, `research`, and `frontend-design`.

Each loadout should remain small, named by purpose, and backed by validation.

### `shared/`

Reusable generic instructions, skills, hooks, MCP fragments, and templates that can be materialized into more than one runtime.

Shared files must not contain private operator history.

### `adapters/`

Runtime-specific translation for Claude Code and Codex.

Adapters answer: how does generic shared/loadout intent become a runtime-shaped file surface?

### `examples/`

Small, safe sample tasks or sample projects for first-run validation.

Examples should avoid external credentials and live-home writes.

### Test and verification surface

The extracted public artifact is optimized as an installable product surface, not
as the full private development checkout. It ships the documented verification
scripts needed for onboarding and release smoke tests; the private repo keeps
the larger maintainer test suite and audit history.

Public verification must prove:

- loadout definitions validate;
- route resolution works;
- sandbox materialization works for Claude and Codex;
- onboarding templates are placeholder-only;
- public docs do not reference missing scripts;
- public smoke commands run in a fresh extracted copy.

## Public review checklist

Before public launch, review these surfaces:

- README: product story, launch flow, closeout flow, install prompt.
- Source/accounting docs: per-loadout attribution lives in `loadouts/*/SOURCES.md`; deeper maintainer evidence stays in the maintainer development workspace and is not shipped.
- `hermes-gateway-skills/`: frozen deterministic skill snapshot.
- `loadouts/`: actual loadout definitions and per-loadout source files.
- `adapters/`: Claude/Codex deterministic materialization.
- `scripts/`: runner, prompt enhancer path, extraction, validation.
- `docs/architecture/`: routing, adapters, Hermes skill control plane.
- `docs/guides/`: onboarding and visible launch contract.
- `.env.example`: placeholder-only, no private values.
- release gate (maintainer): the shipped tree contains what the docs claim and excludes maintainer-only lanes.


### `.github/`

CI should run the same product gate a local user can run.

```bash
python scripts/validate_loadouts.py
python scripts/resolve_route.py --runtime claude --request "Use Claude Code for research" --explicit-loadout research
python scripts/apply_loadout.py --runtime claude --loadout research --output-root output
python scripts/apply_loadout.py --runtime codex --loadout research --output-root output
python scripts/list_runtime_commands.py --compare --loadout research --format markdown
python scripts/smoke_clean_hermes_onboarding.py --json
```

## Private/dev-only lanes

Development-only lanes stay out of the public artifact unless rewritten generically:

```text
operator-only workspace
Hermes local runtime state
Claude/Codex local runtime homes
generated output
caches and runtime homes
private docs, prompts, and planning notes
dated audits/logs not rewritten as public docs
operator/session history
real chat IDs, local paths, tokens
```

## Release rule

A public release is valid only when a fresh extracted copy has this shape, passes the checker, and can be reviewed without private context.
