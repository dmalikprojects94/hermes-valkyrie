# Codex parity and smoke verification notes

Use this reference when the operator asks to run the terminal-loadout system through Codex too, audit Codex/Claude capability parity, or verify watcher/report routing after a hardening pass.

## What to verify

A credible Codex parity pass checks more than whether `codex` launches:

- command inventory resolves for both runtimes and every relevant loadout;
- Codex-managed command equivalents are represented as skills and documented in `docs/codex-installed-capabilities.md`;
- Claude slash commands and Codex command equivalents are compared at the behavior/capability level, not just filename count;
- fresh Codex sessions use startup-prompt transport (`input_transport: initial_prompt`) instead of fragile post-launch paste/send when possible;
- the watcher is configured and records runtime Stop/final-message events;
- closeout produces structured or explicitly unstructured reports, never silent disappearance;
- raw reports route to `$SAVE_DESTINATION_PATH/agents/<runtime>/raw-runs/` when the configured save destination is available;
- project mirrors route under `local-runtime-artifacts/projects/<project>/coding-terminal-runs/` and raw runtime artifacts stay ignored;
- `operator-status --json` is clean after cleanup: no `open_managed`, no `orphan_tmux`, no `runtime_event_recording_failed`, and no unexpected route warnings.

## Mock/smoke pattern

For a non-destructive confidence pass, run these classes of checks from the loadout-system repo:

```bash
python scripts/validate_loadouts.py
python scripts/smoke_clean_hermes_onboarding.py --json
python scripts/list_runtime_commands.py --runtime claude --loadout default
python scripts/list_runtime_commands.py --runtime codex --loadout default
python scripts/apply_loadout.py --runtime claude --loadout default --output-root /tmp/loadout-smoke-claude --format json
python scripts/apply_loadout.py --runtime codex --loadout default --output-root /tmp/loadout-smoke-codex --format json
python scripts/coding_terminal_runner.py operator-status --repo /home/<operator>/projects/<GITHUB_REPO_NAME> --json
```

Also run dry-run starts for both runtimes when changing launch behavior. Confirm Claude and Codex choose the expected prompt transport, and that route preflight reports a save-destination raw root source with the raw root under `$SAVE_DESTINATION_PATH`.

## Live golden-path test

Mock tests do not prove the watcher/reporter end-to-end. After lifecycle/reporting changes, run one live harmless task in both Claude and Codex using visible terminals:

1. preflight `operator-status --json`;
2. start a fresh visible Claude run and a fresh visible Codex run with the same harmless task;
3. wait through the event-driven watcher, not tmux polling as the primary completion signal;
4. confirm structured closeout and both report destinations;
5. run `cleanup-stopped --json` or `stop --manifest ... --json` only after structured closeout with no blockers;
6. final `operator-status --json` must show no open managed sessions or orphan tmux sessions unless deliberately left open for inspection.

Use `--keep-open-after-closeout` by default for the operator-visible verification so the session remains inspectable after closeout. Use `--stop-after-closeout` only when the run is one-shot and the operator explicitly expects successful sessions to close automatically. Otherwise leave visible sessions open intentionally and report their state.

## Operator polish backlog that recurs

When the user asks what is still weak, check these specific surfaces before claiming the system is solid:

- a plain-English `doctor`/health surface on top of `operator-status`;
- `reports list` or equivalent latest-report inventory showing runtime, manifest, raw Obsidian path, project mirror path, closeout status, and lifecycle state;
- top-level `runtime` and `loadout` fields in start responses so operators do not need to inspect nested hook objects;
- stale-run archive/filtering so old closed sessions do not clutter current status;
- route-drift tests for missing/unwritable `OBSIDIAN_VAULT_PATH` and explicit CLI raw-output overrides;
- combined Claude/Codex capability matrix documentation so command drift is visible.
