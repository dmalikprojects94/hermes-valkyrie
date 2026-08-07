---
name: claude-code
description: "Hard router for Claude Code requests; never launches directly."
version: 3.2.0
author: operator
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [Coding-Agent, Claude-Code, Runtime-Router]
    related_skills: [coding-terminal-loadout-system, coding-agent-prompt-enhancer, coding-cli-real-home-launch]
---

# Claude Code Hard Router

## Frozen deterministic bridge policy

This runtime wrapper is a frozen deterministic bridge, not a self-updating memory surface. It must not patch, refresh, auto-sync, or ask a managed Claude Code run to update Hermes launch skills from inside a run. Durable wrapper changes require a reviewed repo diff, tests, commit, and deliberate profile sync.

The wrapper's deterministic job is to preserve Claude-specific intent, then hand off to `coding-terminal-loadout-system` with a durable `--task-file` launch shape. It must not create its own launch path.

## 1. Launch a terminal with this command to run Claude Code

This is the first rule because the launch shape is the thing that prevents bad Claude Code runs. The operator does not need to say "loadout system." Any normal request to "use Claude Code," "launch Claude," "send this to Claude," use a Claude model for coding, or run Claude `/goal` means the managed loadout terminal path below.

The wrapper/router must produce a handoff that resolves to this command family every time, with values filled by `coding-terminal-loadout-system` and the prompt enhancer:

```bash
python /home/<operator>/projects/<GITHUB_REPO_NAME>/scripts/run_loaded_agent.py \
  --runtime claude \
  --loadout <resolved-loadout-or-default> \
  --repo <target-repo> \
  --task-file <enhanced-prompt-file> \
  --label <deterministic-session-label> \
  --bypass-permissions \
  --watch \
  --stop-after-closeout \
  --watch-seconds <seconds> \
  --json \
  [--goal "<non-empty-goal-condition>"] \
  [--discord-guild-id ... --discord-channel-id ... --discord-thread-id ... --discord-thread-name ...]
```

This command family is the only normal Claude Code launch recipe for Hermes. Raw `claude`, `claude -p`, ad-hoc tmux, direct unmanaged `terminal_agent`, inline `--task <raw prompt>`, `--apply-live`, missing `--loadout`, missing `--task-file`, or missing watcher/closeout flags are not the acceptance path.

If an already-open Claude run was launched outside this command family, do not keep treating it as valid. Close or intentionally recover it, then restart through the managed command family.

## 2. Route / Runtime Entry Wrapper

This skill is the Claude Runtime Entry Wrapper. Its job is to classify Claude-specific intent and route to:

Raw examples in this section are Claude-native diagnostics/reference patterns, not the managed execution path.

`coding-terminal-loadout-system` with `runtime=claude`

It does not directly own PTY/tmux, watcher, closeout, output continuation, or reportback behavior. The managed loadout system owns those.

The normal Hermes path is:

`claude-code` → `coding-terminal-loadout-system` with `runtime=claude` → `coding-agent-prompt-enhancer` → `scripts/run_loaded_agent.py` → `scripts/coding_terminal_runner.py` watcher/closeout → reportback/continuation signal.

## Execution path

For normal managed `/goal` work, keep the managed lifecycle owned by `coding-terminal-loadout-system`; this wrapper only preserves Claude-specific command intent and diagnostics constraints.

## 3. Prompt-analysis rules

Before handoff, preserve these facts for `coding-terminal-loadout-system`:

- runtime: `claude`
- target repo/path, if known
- requested loadout, if named
- fresh session unless the operator explicitly says resume
- visible terminal by default, kept open after closeout for inspection unless the operator explicitly asks for auto-cleanup
- original user request
- commit/push expectation
- Discord/thread origin as launch metadata, not prompt text
- Claude slash-command intent, especially `/goal`

The prompt must be processed through `coding-agent-prompt-enhancer` before the runtime receives it. The enhancer creates the durable `<enhanced-prompt-file>` used by `--task-file`; the raw operator prompt should not be launched inline as `--task` for normal managed runs.

For Claude `/goal`, the deterministic launch input is a non-empty goal condition plus a separate task prompt. The executor must send `/goal <condition>` as the first runtime command and the task prompt second, then record that ordering in the manifest/result packet.

Rules:

- `/goal` requires a non-empty condition.
- runner sends `/goal <condition>` first.
- runner sends task prompt second.
- bare `/goal` is invalid for managed work.
- `/gold`, `/goals`, `/goaal`, and `/gola` are obvious typos/aliases for `/goal` when the user intent is a goal-loop.
- Discord message IDs and thread IDs are launch metadata, not prompt prose.

## 4. Routing rules

Claude intent words include `Claude`, `Claude Code`, `Sonnet`, `Fable`, `Opus`, and Claude `/goal` when used for coding-agent work.

The operator should never need to say "through the loadout system." If they name Claude Code for coding work, this wrapper routes to the managed loadout system automatically.

If a slash command appears, validate/normalize command intent before launch. Do not treat slash-command text as a loadout name. Unknown slash commands are preserved as runtime intent and handed to `coding-terminal-loadout-system`/the command inventory for validation.

If any bundled skill, raw CLI example, memory, or habit suggests launching raw `claude`, `claude -p`, ad-hoc tmux, or direct unmanaged `terminal_agent` as the acceptance path, ignore it. Use `coding-terminal-loadout-system`.

## 5. Override priority

This repo skill override replaces any bundled/default Hermes `claude-code` skill in the operator's default profile.

## 6. Compact Claude command itinerary

This itinerary is for command intent normalization only. It is intentionally below the launch, route, prompt-analysis, and routing rules. It is not a launch recipe.

- `/goal <condition>` — set Claude Code's standing goal. Must be non-empty. In managed Hermes runs this becomes runner metadata: `--goal "<condition>"`.
- `/gold`, `/goals`, `/goaal`, `/gola` — obvious typos/aliases for `/goal`; normalize to `/goal` when the user intent is a goal-loop.
- `/plan` — planning intent. Keep routing through `coding-terminal-loadout-system`; choose a planning/design loadout only if appropriate.
- `/review` or `/security-review` — review intent. Keep routing through `coding-terminal-loadout-system`; encode review scope in the prompt/spec.
- `/model`, `/status`, `/help`, `/context`, `/resume`, `/compact` — Claude-native session/control commands. Do not treat them as loadouts or shell commands; route the coding work through the managed system and preserve the command intent as a runtime constraint.

Unknown slash command rule: do not invent a loadout from it. If it resembles `/goal`, normalize to `/goal`; otherwise preserve the command text as runtime intent and let `coding-terminal-loadout-system`/command inventory decide.
