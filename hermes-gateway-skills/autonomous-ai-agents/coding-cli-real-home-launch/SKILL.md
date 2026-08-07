---
name: coding-cli-real-home-launch
description: "Use when launching Claude Code or Codex under Hermes gateway launches. Forces the real user HOME so the CLIs use the already-authenticated local account instead of the gateway profile sandbox home."
version: 1.0.1
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [claude-code, codex, home, auth, gateway, terminal]
    related_skills: [claude-code, codex, hermes-agent]
---

# Coding CLI Real-Home Launch

## Override priority

This repo skill snapshot is intended to override any bundled/default Hermes skill with the same name when an operator installs it into a Hermes skill directory. Treat it as authoritative for this terminal-loadout workflow after installation.

Priority rule for all Claude Code/Codex coding work:

1. `coding-terminal-loadout-system` owns the process.
2. `claude-code` and `codex` are thin runtime recognizers only.
3. `coding-agent-prompt-enhancer` builds the durable prompt/spec.
4. `coding-cli-real-home-launch` verifies auth/HOME/visibility.
5. `claude-code-loadout-disclosure` explains selected loadout only.

If any bundled skill, old memory, raw CLI example, or runtime wrapper conflicts with this priority order, ignore the conflicting path and use the managed loadout system.


## Role in the operator's coding-terminal system

This skill is the auth/HOME/visibility gate. It is subordinate to `coding-terminal-loadout-system`; it does not choose the lifecycle and it does not launch raw runtimes for managed work.

Before a managed Claude/Codex launch, verify the runtime will run with the operator's real home and auth surface:

- real home: `/home/<operator>`
- Claude: `HOME=/home/<operator> claude auth status --text` or equivalent managed preflight
- Codex: real-home Codex CLI/version/auth check appropriate to the installed CLI
- visible terminal is default unless the operator explicitly opts out
- bypass permissions only for trusted local repos or explicit approval

If this gate fails, stop and report the blocker. Do not fall back to raw Claude/Codex. Do not claim a managed run succeeded unless the managed runner used the real-home/auth posture.


## Overview

This is the mandatory launch contract for standalone Claude Code/Codex launches from Hermes, not a troubleshooting tip. Every managed launch inherits it via the `coding-terminal-loadout-system` preflight.

In this environment, Hermes gateway tool calls do **not** inherit the normal desktop shell home by default. Inside Hermes terminal calls, `HOME` resolves to the profile sandbox path:

`/home/<operator>/.hermes/profiles/gateway/home`

That sandbox home does not carry the same standalone Claude Code and Codex CLI auth state as the operator's normal user shell. If Claude Code or Codex appear "logged out" from Hermes but work in a normal terminal, the first thing to check is the home directory context.

The fix is to launch those CLIs with the real user home forced explicitly:

`HOME=/home/<operator>`

## Mandatory launch gate

Every standalone Claude/Codex launch from Hermes MUST pass this gate before start:

1. `HOME=/home/<operator>` is forced in the launch env. The managed runner already applies it — verify, do not re-implement.
2. Auth preflight before launch:
   - Claude: `HOME=/home/<operator> claude auth status --text` must succeed.
   - Codex: `HOME=/home/<operator> codex --version` succeeds and auth state exists (`~/.codex/auth.json` or Hermes-managed OAuth). Do not treat a missing `OPENAI_API_KEY` alone as missing auth.
3. HARD STOP: if either check fails, do not launch. Report the exact failing command and its output to the operator.
4. For Codex with a materialized runtime home, `CODEX_HOME` points at the applied home with `auth.json` bridged per `references/repo-local-codex-home-auth-bridge.md`.

A run launched past a failed gate is not a managed run; it cannot satisfy the Done-means-done checklist in `coding-terminal-loadout-system`. For a managed Discord-origin run, "done" requires watcher terminal state, structured closeout, verified report routing, AND a recorded postback/continuation decision (posted, or an explicit blocked/needs-review state reported to the operator) — closeout alone is NOT done.

## When to Use

Always — via the `coding-terminal-loadout-system` executor preflight. Secondary symptom triggers:

- Claude Code works in the operator's normal terminal but Hermes reports "Not logged in"
- Codex works in the operator's normal terminal but Hermes gets 401 / missing auth
- Need Hermes to open a real coding-agent terminal session using the same auth context the operator uses manually
- Need reliable operational launch commands for Claude Code and Codex on this native Ubuntu laptop

Do not use this skill for Hermes-internal model routing. This is specifically for the **standalone** `claude` and `codex` CLIs.

## Exact Launch Pattern

Always prepend the real home export before invoking the CLI.

### Claude Code

Interactive launch:

```bash
export HOME=/home/<operator>
cd /target/path
claude
```

One-shot print mode:

```bash
export HOME=/home/<operator>
cd /target/path
claude -p "<prompt>" --max-turns 2
```

Authentication check:

```bash
HOME=/home/<operator> claude auth status --text
```

### Codex

Interactive launch:

```bash
export HOME=/home/<operator>
cd /target/git/repo
codex
```

One-shot task:

```bash
export HOME=/home/<operator>
cd /target/git/repo
codex exec "<prompt>"
```

Version/auth sanity check:

```bash
HOME=/home/<operator> codex --version
```

## Hermes Tool Usage Pattern

When this behavior is being restored into a Hermes loadout stack, do **not** leave it as an operator-only note. Encode it into the loadout system as runtime launch metadata so Hermes can consume it automatically.

See also: `references/loadout-integration.md`, `references/restart-smoke-verification.md`, and `references/runtime-event-completion-watch.md`.

When the launch is a visible Claude Code or Codex coding terminal, wire runtime-native completion into the manifest and have Hermes run an event-driven watcher over the manifest artifact directory. Prefer OS-level filesystem notifications such as Linux `inotify`; use 25-30 second event-only polling only as a fallback. Do not use tmux pane capture as the primary completion detector; tmux is the control/view layer, while `Stop`/`turn.completed` events are the state signal.

When calling the Hermes `terminal` tool, use commands shaped like:

```bash
export HOME=/home/<operator>; cd /target/path; claude
```

```bash
export HOME=/home/<operator>; cd /target/git/repo; codex
```

For interactive long-lived sessions, do **not** assume Hermes `process` writes are the safest input bridge for fullscreen Claude/Codex TUIs. In this environment, if prompt text integrity matters, prefer a tmux-backed session and drive input with `tmux send-keys`; use a visible desktop terminal only as the viewer/attachment layer. See `references/tmux-visible-claude-input.md`.

Example Claude one-shot test:

```bash
export HOME=/home/<operator>; cd /home/<operator>; claude -p 'Create a short numbered plan for building a simple calculator app. Keep it concise.' --max-turns 2
```

Example Codex one-shot test:

```bash
export HOME=/home/<operator>; cd /tmp/some-git-repo; codex exec 'Create a short numbered plan for building a simple calculator app. Keep it concise.'
```

## Verification Checklist

- Mandatory launch gate: HOME forced, auth preflight passed, stop-on-fail honored
- `echo $HOME` inside the launched shell shows `/home/<operator>`
- `claude auth status --text` succeeds under forced HOME
- Codex responds successfully under forced HOME
- If Codex is used, current directory is a git repo
- If interactive mode is used, Hermes terminal call has `pty=true`
- If a Hermes loadout shim is involved, dry-run verification uses a temp output root and does **not** rewrite `~/.claude` or `~/.codex`
- Before the first live `--target-home` apply, create rollback archives for both runtime homes
- For Codex launchers that materialize a managed home, confirm `CODEX_HOME` is set to that applied runtime home
- For integrated `hermes loadout launch` verification, prefer a two-stage smoke: first a one-line success sentinel, then an env-report prompt that returns `HOME`/`PWD` and `CODEX_HOME` for Codex
- Use the forwarded-argument form `--arg=<value>` when passing runtime flags like `-p` or `--max-turns` through `hermes loadout launch`
- When Hermes exposes a `terminal_agent` or similar integrated launcher, verify that the operator-visible tool preview and completion line both show the human-friendly runtime label plus the resolved loadout name (for example `Claude Code · loadout deep-coding`)
- Add a repo-owned smoke verifier for mature integrations so operators can re-run the full path after restarts or merges; it should check live and dry-run launch behavior plus `applied_loadout`, `launch_notice`, and the rendered runtime/loadout preview path
- For final user-level validation, test the integrated launcher path itself (`terminal_agent` or `hermes loadout launch`), not only direct raw `claude` / `codex` CLI invocations
- For completion-aware visible coding terminals, verify the event-only path directly: a runtime hook writes `events.jsonl` / `last_runtime_event` into the manifest, the launcher auto-starts a background `watch-start --event-only --event-driven` process after prompt send, and `coding_terminal_runner.py watch-status --json` can see the watcher/result without tmux capture. For long waits, prefer filesystem-event wakeups; use `--poll-interval 30` only as fallback.
- For interactive validation of full-screen TUIs, treat startup correctness as its own checkpoint: correct repo, correct loadout banner, correct HOME / CODEX_HOME, and successful prompt entry. If the Hermes process bridge cannot cleanly surface the final TUI reply, record that limitation explicitly instead of treating the integration as failed
- For interactive slash-command validation, first send a very short plain-text control prompt and compare the exact intended text to the PTY/log echo before testing `/goal` or other slash commands. Only claim slash-command success if the control prompt and the slash command both arrive intact; see `references/interactive-input-integrity-check.md`
- If direct Hermes PTY/process writes distort Claude input, switch to the tmux-backed visible-input workflow in `references/tmux-visible-claude-input.md` before concluding the runtime or loadout is broken
- When handing validation to the operator, condense it into a very short exact checklist rather than a broad test plan
- For repo-local Claude loadout proof without touching repo code, launch Claude visibly with the generated `output/claude/CLAUDE.md` passed via `--append-system-prompt-file`, and capture the PTY with `script -q -f -a <log> -c '... claude ...'` so you can prove the exact appended loadout file, working directory, and startup response after launch

## Common Pitfalls

1. **Using the gateway profile home by accident.** Default Hermes terminal HOME here is `/home/<operator>/.hermes/profiles/gateway/home`, which can make Claude/Codex appear unauthenticated.

2. **Assuming Hermes-internal auth equals standalone CLI auth.** Hermes model auth and standalone CLI auth are separate contexts.

3. **Running Codex outside a git repo.** `codex` and especially `codex exec` are happiest inside a repo; for scratch tests create a temp repo first.

4. **Testing auth without forcing HOME.** A failed auth test is not meaningful on this setup unless the command was run with `HOME=/home/<operator>`.

5. **Using non-interactive launches when the operator wants visible agent behavior.** Prefer real PTY terminal sessions when the goal is to verify the coding agent is actually operating on screen.

5a. **Starting tmux without a desktop viewer.** For the operator's current workflow, `tmux new-session -d ... claude` is only the control plane. It still must be paired with a real visible desktop terminal window attached to the tmux session, and desktop-window proof (not just `tmux list-clients`) must exist before calling the run visible.

6. **Stopping at documentation only when the system has a loadout layer.** If Claude/Codex launch behavior is governed by a loadout repo or runtime adapter, save the real-HOME rule there too — as machine-readable launch metadata, not just prose.

7. **Letting dry-run mutate the live homes.** In a Hermes loadout shim, dry-run should materialize into a temporary output root and report the would-be manifest and command from there. Do not let preview mode rewrite `~/.claude` or `~/.codex`.

8. **Forgetting rollback archives before the first live apply.** Before introducing `--target-home` writes, archive both runtime homes so recovery is cheap.

9. **Omitting `CODEX_HOME` when launching Codex from a managed runtime home.** Forced `HOME=/home/<operator>` preserves auth context, but the launched Codex process should still see `CODEX_HOME=<applied runtime home>` when the loadout system materializes a specific Codex surface.

10. **Forgetting that repo-local `CODEX_HOME` may not contain Codex OAuth state by default.** If a repo-local applied Codex home starts unauthenticated even though Codex works in the operator's normal terminal, keep `HOME=/home/<operator>`, preserve the repo-local `CODEX_HOME`, and bridge auth into that applied home by linking `auth.json` from the real `~/.codex` rather than copying secrets or falling back to the global Codex home.

11. **Trying to restart the gateway from inside the gateway process.** Hermes may refuse this to avoid restart loops. For post-integration verification, use a detached out-of-band restart trigger instead of an in-process `hermes gateway restart`.

11. **Fixing operator shell commands but not the Hermes adapter defaults.** If `hermes loadout status`, `hermes loadout launch`, or `terminal_agent` still derive paths from gateway `Path.home()`, the integration will look documented but remain broken in the live gateway session.

12. **Emitting `launch.env` in manifests without applying it to the subprocess.** The manifest is only a contract. The launcher must merge that env into the actual child process or the runtime will still come up under the wrong auth/config context.

13. **Calling the raw CLI and assuming the integrated launcher is therefore verified.** For Hermes-side acceptance, validate `terminal_agent` or `hermes loadout launch` directly so adapter bugs are caught.

14. **Treating PTY/TUI automation limits as integration failures.** For Claude/Codex interactive checks over Hermes, a durable pass can be: launcher banner correct, repo correct, loadout correct, trust/startup flow handled, and prompt text accepted. The final rendered assistant reply may still require a human-visible terminal if the process bridge cannot faithfully capture the fullscreen UI.
14. **Treating PTY/TUI automation limits as integration failures.** For Claude/Codex interactive checks over Hermes, a durable pass can be: launcher banner correct, repo correct, loadout correct, trust/startup flow handled, and prompt text accepted. The final rendered assistant reply may still require a human-visible terminal if the process bridge cannot faithfully capture the fullscreen UI.
15. **For visible repo-local loadout verification, capture hard proof instead of only saying Claude launched.** When the loadout is materialized under a repo output root rather than a live runtime home, start a real desktop terminal, prepend a short manifest prelude (`HOME`, repo path, manifest path, selected loadout), run Claude with `--append-system-prompt-file <repo-output>/CLAUDE.md`, and record the whole PTY with `script`. This gives exact proof of the applied loadout without mutating repo code or the user's live `~/.claude` surface.
16. **ANSI-heavy PTY logs are still useful evidence.** Even if the captured `script` log contains terminal escape sequences, preserve the lines that show the Claude command, appended prompt file path, printed proof lines, and confirmation sentence; those are sufficient to verify visible launch behavior.
17. **When Claude output shape is drifting, inspect the materialized runtime surface before blaming the task prompt.** In loadout-driven Claude systems, the real behavior often comes from generated `CLAUDE.md`, generated command files, and post-run hooks. If those generated files only carry short `Purpose` stubs or a loose reporting note, Claude will naturally return unstructured prose even when richer source skills exist elsewhere in the repo.
18. **Treat structured-output reliability as a launch-contract concern, not just a wording concern.** For tasks that must come back parseable, the loadout/integration layer should preserve explicit section contracts in generated `CLAUDE.md`/command docs and, when appropriate, launch Claude with machine-readable flags like `-p --output-format json` or `--json-schema` rather than relying only on natural-language prompt tightening.
19. **If fullscreen Claude input is corrupted through Hermes PTY/process writes, verify the same launch through tmux before blaming Claude, the repo, or the loadout.** A clean tmux `send-keys` pass is strong evidence that the bug is in the transport layer, not the runtime configuration; see `references/tmux-visible-claude-input.md`.
20. **For visible interactive proof in this environment, separate the viewer from the input transport.** A real desktop terminal window can remain the user-visible surface, while tmux serves as the authoritative input/output control plane underneath.
21. **Do not use stale Codex automation flags.** Codex CLI 0.139.0 rejects the old `--full-auto` flag. For unattended/high-trust smoke runs use `--dangerously-bypass-approvals-and-sandbox`, and for generated hook commands also include `--dangerously-bypass-hook-trust`.
22. **Do not let startup statuses masquerade as completion.** Event-only watchers should ignore `blocked` / `waiting_for_input` manifest states until a real runtime event exists in `events.jsonl` or `last_runtime_event`; otherwise a watcher can wake before Claude/Codex has actually started working.

## Hermes Loadout Shim Pattern

When Hermes is being taught to consume an external Claude/Codex loadout repo, keep Hermes thin.

See also: `references/loadout-integration.md`, `references/restart-smoke-verification.md`, `references/visible-repo-local-loadout-proof.md`, and `references/repo-local-codex-home-auth-bridge.md`

When the operator specifically wants to see the Claude session on-screen and also needs exact evidence of a repo-local applied loadout, use the visible proof recipe in `references/visible-repo-local-loadout-proof.md`.
For repo-local Codex homes, also consult `references/repo-local-codex-home-auth-bridge.md` so the applied `CODEX_HOME` keeps using the already-authenticated standalone Codex account without copying secrets.
If the user wants proof that interactive slash commands themselves work through Hermes, run the control-path check in `references/interactive-input-integrity-check.md` before claiming success.

1. Treat the external repo as the source of truth for loadout definitions, routing, inheritance, merge logic, materialization, and manifest shape.
2. Add a Hermes operator CLI such as `hermes loadout ...` for `status`, `resolve`, `apply`, and `launch`.
3. Add an agent-facing launcher surface such as `terminal_agent` for one-shot runtime delegation.
4. In dry-run flows, apply to a temporary output root instead of the live runtime home.
5. In live-launch flows, apply to the real runtime home, then launch with the correct environment.
6. Resolve the real user home in the Hermes adapter layer itself; do not rely on per-command shell exports or `Path.home()` defaults inside the gateway process.
7. Provide an explicit override such as `HERMES_LOADOUT_USER_HOME` so tests and future deployments can force the intended login-user home deterministically.
8. Merge manifest-defined `launch.env` into the actual subprocess environment before spawn; documenting `HOME=/home/<operator>` in YAML is not enough if the launcher does not apply it.
9. Preserve and inspect `hermes-loadout.json` as proof of the active surface.
10. Keep Claude on the default live home unless the runtime contract explicitly supports overrides.
11. For Codex, preserve the real `HOME=/home/<operator>` rule for auth context and set `CODEX_HOME` to the applied runtime home when launching.
12. If the applied Codex home is repo-local and Codex auth lives only in the real `~/.codex`, bridge that auth into the applied `CODEX_HOME` with a symlink to `auth.json` instead of copying credentials or abandoning the repo-local surface.
13. Treat adapter runtime maps as executable contract, not passive docs. Materializers, validators, and emitted manifests should all agree on the same machine-readable managed-path map.
14. If a gateway restart is needed to verify the integrated surface, trigger it out-of-band. Do not call a self-restart path from inside the live gateway process if Hermes protects against restart loops.
15. Pair restart verification with a detached smoke script that restarts the service, waits for it to come back, runs `hermes loadout status`, performs Claude/Codex dry-run launches, reruns the targeted tests, and confirms integrated tool-run messaging still reports runtime + resolved loadout correctly.

See also: `references/loadout-integration.md`, `references/runtime-map-contract.md`, `references/gateway-home-resolution.md`, and `references/restart-smoke-verification.md`

## Runtime-Map Contract Rule

When integrating Hermes with an external loadout repo, do not hardcode runtime layout in the launcher/materializer if a runtime-map file exists.

The adapter runtime map should be the source of truth for things like:

- managed directories and filenames for commands, agents, skills, hooks, MCP, config, and manifest metadata
- whether apply output is being written to a repo-local preview root or a live runtime home
- the manifest location Hermes should inspect after apply

Minimum enforcement for this class of work:

1. Validator loads every runtime map and fails if required keys are missing.
2. Materializers read managed-path values from the runtime map instead of hardcoded paths.
3. Apply results expose enough metadata for Hermes/operators to inspect the write layout without guessing.
4. Tests cover both repo-local apply and live-home apply shapes.

Recommended manifest/result fields:

- `target_mode`
- `runtime_managed_paths`
- `manifest_path`
- `managed_files`

## Loadout-System Integration Rule

If Hermes is using a Claude/Codex loadout system, persist this rule in the runtime launch contract for both runtimes.

Minimum shape to preserve:

- `launch.env.HOME=/home/<operator>`
- a shell prefix such as `export HOME=/home/<operator>`
- runtime examples for Claude and Codex launch commands
- a short note explaining that the gateway profile sandbox home is the wrong auth context for standalone coding CLIs in this environment

Verification for that integration class:

1. Apply the loadout and inspect the emitted JSON or manifest.
2. Confirm the `launch` block is present for both `claude` and `codex`.
3. Confirm generated runtime surface docs mention `HOME=/home/<operator>`.
4. Run the loadout validator/tests after patching the repo.
