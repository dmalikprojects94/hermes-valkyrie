# Clean Hermes sandbox testing

Use this guide when you want to prove the terminal loadout system can be installed into a fresh Hermes-style environment before publishing a public repo.

The goal is to test the product artifact, not the maintainer's development checkout. The sandbox uses a clean public copy, a temporary `HERMES_HOME`, a temporary `HOME`, and no live credentials.

## What this proves

The clean sandbox smoke proves that:

- the sanitized public copy can be generated or copied into a clean checkout;
- the public Hermes bridge skills can be installed into an isolated Hermes skills directory;
- the loadouts validate without private state;
- Claude and Codex routes resolve from a fresh checkout;
- Claude and Codex loadouts materialize into `output/` instead of live runtime homes;
- `run_loaded_agent.py --dry-run --watch --json` plans watcher and closeout behavior without launching Claude Code or Codex;
- no Discord, Slack, GitHub, email, or external reportback target is used.

It does not prove authenticated live Claude Code/Codex execution. That requires a separate operator-approved canary after the sandbox passes.

## Run the sandbox smoke

From the repo root:

```bash
python scripts/smoke_clean_hermes_onboarding.py
```

For a machine-readable report:

```bash
python scripts/smoke_clean_hermes_onboarding.py --json
```

To keep the temporary public copy and isolated Hermes home for inspection:

```bash
python scripts/smoke_clean_hermes_onboarding.py --keep-tmp --json
```

Expected summary:

```text
clean_hermes_onboarding_smoke=PASS
installed_bridge_skills=6
managed_launch=dry-run watcher_default=true closeout_default=true runtime_event_closeout=true
live_runtime_launched=false external_reportback_used=false
```

## Sandbox boundaries

The harness intentionally sets isolated environment variables for the child checks:

```text
HOME=<temporary operator home>
HERMES_HOME=<temporary Hermes home>
HERMES_PROFILE=clean-onboarding-smoke
SAVE_DESTINATION_PATH=<temporary save destination>
```

It also clears legacy vault-path variables that could leak maintainer state into route tests.

## When to run this

Run this before relying on a checkout for onboarding. It should pass from any clean public checkout.

Use this as the public-readiness proof before any live-home setup or authenticated runtime canary.

## After it passes

The next optional proof is an approval-gated canary:

```text
I approve one sandboxed live-runtime canary for <claude|codex>. Use a harmless read-only task file, keep external reportback disabled, keep secrets out of tracked files, and report the manifest, watcher status, closeout artifact, and cleanup state.
```

Do not run that canary until the operator explicitly approves it.
