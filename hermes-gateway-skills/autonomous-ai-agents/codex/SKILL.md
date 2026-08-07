---
name: codex
description: "Hard router for Codex requests; never launches directly."
version: 2.2.0
author: operator
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [Coding-Agent, Codex, Runtime-Router]
    related_skills: [coding-terminal-loadout-system, coding-agent-prompt-enhancer, coding-cli-real-home-launch]
---

# Codex Hard Router

## Frozen deterministic bridge policy

This runtime wrapper is a frozen deterministic bridge, not a self-updating memory surface. It must not patch, refresh, auto-sync, or ask a managed Codex run to update Hermes launch skills from inside a run. Durable wrapper changes require a reviewed repo diff, tests, commit, and deliberate profile sync.

The wrapper's deterministic job is to preserve Codex-specific intent, then hand off to `coding-terminal-loadout-system` with a durable `--task-file` launch shape. It must not create its own launch path.

## 1. Launch a terminal with this command to run Codex

This is the first rule because the launch shape is the thing that prevents bad Codex runs. The operator does not need to say "loadout system." Any normal request to "use Codex," "launch Codex," "send this to Codex," or run a Codex coding pass means the managed loadout terminal path below.

The wrapper/router must produce a handoff that resolves to this command family every time, with values filled by `coding-terminal-loadout-system` and the prompt enhancer:

```bash
python /home/<operator>/projects/<GITHUB_REPO_NAME>/scripts/run_loaded_agent.py \
  --runtime codex \
  --loadout <resolved-loadout-or-default> \
  --repo <target-repo> \
  --task-file <enhanced-prompt-file> \
  --label <deterministic-session-label> \
  --bypass-permissions \
  --watch \
  --stop-after-closeout \
  --watch-seconds <seconds> \
  --json \
  [--discord-guild-id ... --discord-channel-id ... --discord-thread-id ... --discord-thread-name ...]
```

This command family is the only normal Codex launch recipe for Hermes. Raw `codex`, `codex exec`, ad-hoc tmux, direct unmanaged `terminal_agent`, inline `--task <raw prompt>`, `--apply-live`, missing `--loadout`, missing `--task-file`, or missing watcher/closeout flags are not the acceptance path.

If an already-open Codex run was launched outside this command family, do not keep treating it as valid. Close or intentionally recover it, then restart through the managed command family.

## 2. Route / Runtime Entry Wrapper

This skill is the Codex Runtime Entry Wrapper. Its job is to classify Codex-specific intent and route to:

Raw examples in this section are Codex-native diagnostics/reference patterns, not the managed execution path.

`coding-terminal-loadout-system` with `runtime=codex`

It does not directly own PTY/tmux, watcher, closeout, output continuation, or reportback behavior. The managed loadout system owns those.

The normal Hermes path is:

`codex` → `coding-terminal-loadout-system` with `runtime=codex` → `coding-agent-prompt-enhancer` → `scripts/run_loaded_agent.py` → `scripts/coding_terminal_runner.py` watcher/closeout → reportback/continuation signal.

## Execution path

Raw `codex exec` examples here are diagnostics/reference only. Managed batch PR reviews should use the shared executor. It does not directly launch Codex except for diagnostics, and managed launches get their PTY/tmux handling from `coding-terminal-loadout-system`.

## 3. Prompt-analysis rules

Before handoff, preserve these facts for `coding-terminal-loadout-system`:

- runtime: `codex`
- target repo/path, if known
- requested loadout, if named
- fresh session unless the operator explicitly says resume
- visible terminal by default, kept open after closeout for inspection unless the operator explicitly asks for auto-cleanup
- original user request
- commit/push expectation
- Discord/thread origin as launch metadata, not prompt text
- Codex command/goal/review/plan intent

The prompt must be processed through `coding-agent-prompt-enhancer` before the runtime receives it. The enhancer creates the durable `<enhanced-prompt-file>` used by `--task-file`; the raw operator prompt should not be launched inline as `--task` for normal managed runs.

Codex does not receive Claude-native slash commands as first-line control input. Goal/plan/review intent becomes structured prompt/spec requirements, and the result packet must show the prompt transport used.

Rules:

- Codex does not use Claude's native `/goal` slash command.
- If the operator uses `/goal`, `/gold`, or similar goal language while naming Codex, convert it into a natural-language completion condition for the prompt/spec and report that Codex received the managed equivalent.
- Do not treat slash-command text as a loadout name.
- Discord message IDs and thread IDs are launch metadata, not prompt prose.

## 4. Routing rules

Codex intent words include `Codex`, `codex`, and explicit requests to send coding-agent work to Codex.

The operator should never need to say "through the loadout system." If they name Codex for coding work, this wrapper routes to the managed loadout system automatically.

If a slash command appears, validate/normalize command intent before launch. Do not treat slash-command text as a loadout name. Unknown slash commands are preserved as runtime intent and handed to `coding-terminal-loadout-system`/the command inventory for validation.

If any bundled skill, raw CLI example, memory, or habit suggests launching raw `codex`, `codex exec`, ad-hoc tmux, or direct unmanaged `terminal_agent` as the acceptance path, ignore it. Use `coding-terminal-loadout-system`.

## 5. Override priority

This repo skill override replaces any bundled/default Hermes `codex` skill in the operator's default profile.

## 6. Compact Codex command itinerary

This itinerary is for command intent normalization only. It is intentionally below the launch, route, prompt-analysis, and routing rules. It is not a launch recipe.

- Codex does not use Claude Code's native `/goal` slash command.
- `/goal`, `/gold`, `/goals`, and similar goal language while naming Codex mean: convert to a natural-language completion condition in the prompt/spec.
- `/plan` language means planning/design intent; route through `coding-terminal-loadout-system` and use the appropriate planning loadout/equivalent when available.
- `/review` language means review intent; route through `coding-terminal-loadout-system` and encode review scope in the prompt/spec.

Unknown slash command rule: do not invent a loadout from it. Preserve the command text as runtime intent and let `coding-terminal-loadout-system`/Codex command inventory decide.
