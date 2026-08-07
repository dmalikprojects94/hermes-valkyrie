# Managed Visible Launch Contract

Use this guide when Hermes or another orchestrator is expected to launch Claude Code or Codex, not merely prepare files for them.

The contract removes ambiguity between four different events:

1. **Surface prepared** — the loadout files were materialized.
2. **Runtime process executed** — Claude Code or Codex started somewhere.
3. **Terminal surfaced visibly** — a desktop terminal window opened for the operator.
4. **Run completed** — watcher, closeout, reportback, and lifecycle checks succeeded.

A system is not proven by one of those events alone. A visible managed launch must prove all applicable stages.

## Canonical launch shape

Normal orchestrated launches must go through a managed runner or a wrapper that emits the same command family:

```bash
python scripts/run_loaded_agent.py   --runtime <claude|codex>   --loadout <loadout-name>   --repo <target-repo>   --task-file <enhanced-prompt-file>   --bypass-permissions   --watch   --keep-open-after-closeout   --watch-seconds <seconds>   --json
```

Wrappers may add origin/reportback metadata, a deterministic `--label`, or runtime-specific options such as Claude `/goal` metadata. They must not remove the managed prompt file, watcher, loadout fields, or bypass-required permission posture.

For normal managed work, `--bypass-permissions` is a hard invariant, not an optional convenience flag. The lower start layer must refuse a managed launch before tmux startup if the managed caller omits bypass posture, and the final runtime command must contain the runtime-specific dangerous flag: Claude Code uses `--dangerously-skip-permissions`; Codex uses `--dangerously-bypass-approvals-and-sandbox`.

For Claude Code, the managed runtime adapter must pin the model explicitly on launch. The current default is:

```text
claude --model claude-fable-5
```

Do not rely on Claude Code's remembered/default model state for managed runs. `claude-fable-5` is the pinned default model ID; short aliases such as `fable` or `mythos` may be unavailable even when the underlying model is available. Intentional overrides must be explicit launch configuration — set `HERMES_CLAUDE_MODEL` (or `CLAUDE_CODE_MODEL`) — not accidental TUI state.

## Prompt-file requirement

The runtime prompt must be written to a durable file before launch. The prompt file should include:

- original operator request;
- target repo/path;
- selected runtime and loadout;
- scope and non-goals;
- safety and permission posture;
- verification commands;
- expected closeout/reportback shape.

Do not use inline `--task "..."` as the normal orchestrated path. Inline task text is acceptable only for narrow diagnostics or dry-run probes that are explicitly labeled as such.

## Bad-launch signatures

Stop and classify the launch as misconfigured if the emitted command has any of these signatures:

- raw `claude`, raw `codex`, or `codex exec` as the normal orchestrated path;
- ad-hoc tmux sessions outside the managed runner;
- missing `--loadout`;
- missing `--task-file`;
- inline `--task` for normal work;
- missing `--watch`;
- missing `--bypass-permissions` on a normal managed launch;
- final Claude command missing `--dangerously-skip-permissions`;
- final Codex command missing `--dangerously-bypass-approvals-and-sandbox`;
- `--stop-after-closeout` for an operator-visible verification run;
- Claude Code launch command missing `--model claude-fable-5` unless an explicit model override is recorded;
- no origin/reportback metadata when the operator expects a chat/thread report;
- no manifest or run ledger to inspect after launch.

## Visible-terminal proof

A tmux session is the control plane. It is not by itself proof that the operator saw a terminal.

A visible launch requires desktop-window proof, such as:

- a manifest field like `visible_terminal_proof.status == "desktop_window"`;
- window IDs recorded for the launched terminal title;
- equivalent Computer Use / accessibility / window-manager evidence.

`tmux list-clients` or `visible_terminal_proof.status == "attached_client"` proves only that a PTY attached to tmux. It does not prove a GUI terminal surfaced on the operator's desktop.

If the runtime executed but desktop-window proof is missing, report:

```text
Runtime execution happened, but visible desktop launch is unproven.
```

If tmux attached without desktop evidence, classify it as:

```text
tmux_attached_without_desktop_proof
```

Do not explain that as auto-close unless there is separate evidence that a desktop window opened and then closed.

## Closeout proof

A completed managed run should prove:

- runtime and loadout used;
- prompt file path;
- manifest path;
- visible-terminal proof when visibility was requested;
- watcher started and observed a runtime/terminal completion signal;
- structured closeout was extracted;
- blockers were inspected;
- reportback was posted or intentionally skipped;
- session lifecycle is known (`open`, `stopped`, `closed`, or `needs_attention`).

Closeout alone is not enough if reportback was expected. A terminal window alone is not enough if the watcher never observed completion.

## Operator approval gates

Ask the operator before:

- writing to a live runtime home;
- launching an authenticated runtime CLI for real work;
- enabling external reportback transports;
- bypassing permissions in an untrusted repo;
- publishing or pushing public artifacts.

Sandbox materialization and dry-run command inspection are safe defaults.

## Minimal acceptance canary

After installing or changing the managed launch integration, run a no-op or documentation-only canary in a disposable repo. The canary must verify command shape before launch and manifest proof after launch.

Expected command properties:

```text
has run_loaded_agent.py
has --runtime <claude|codex>
has --loadout <name>
has --task-file <path>
has --watch
has --bypass-permissions
has --keep-open-after-closeout
has --json
manifest has permission_posture: managed_bypass_required
manifest has bypass_permissions_effective: true
manifest has required_bypass_flag_present: true
Claude command has --dangerously-skip-permissions
Codex command has --dangerously-bypass-approvals-and-sandbox
Claude command has --model claude-fable-5 unless intentionally overridden
no raw runtime CLI
no inline --task for normal work
no --stop-after-closeout for visible verification
```

Expected manifest/proof properties:

```text
terminal_visible: true
visible_terminal_proof.status: desktop_window
visible_terminal_proof.desktop_window_ids: non-empty
watcher/closeout status: completed or explicit blocker
operator/reportback state: posted, skipped by design, or explicit needs-review
```

If any item is missing, keep the issue in startup/launch work. Do not call onboarding complete.
