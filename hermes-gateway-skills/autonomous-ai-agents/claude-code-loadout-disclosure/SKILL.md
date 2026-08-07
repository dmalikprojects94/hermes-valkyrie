---
name: claude-code-loadout-disclosure
description: "Before launching visible Claude Code sessions, resolve and announce the runtime/loadout being used."
version: 1.0.1
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [claude-code, loadout, tmux, launch, disclosure]
    related_skills: [claude-code, coding-cli-real-home-launch]
---

# Claude Code Loadout Disclosure

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

This skill explains the selected loadout and boundaries to the operator. It is not a launcher and not a prompt enhancer. It runs after routing/loadout selection when the user needs to know what will be active.

It should report:

- runtime selected
- loadout selected and why
- major behavior added by the loadout
- what is intentionally not included
- whether `/goal` or another command is being used
- whether the run will be visible, watched, closeout-managed, and reportback-managed

It must point back to `coding-terminal-loadout-system` for execution and to `coding-agent-prompt-enhancer` for prompt construction. Do not include raw launch instructions as the preferred path.


## Trigger

Use this whenever the operator asks to open, start, launch, activate, or push work into Claude Code, especially visible tmux-backed sessions. This applies from any Hermes gateway surface where this profile's skills are available: quick work, deep work, main chat, Discord threads, and Slack-style work channels.

## Rule

A Claude Code launch should include an operator-visible loadout notice before or alongside the terminal launch. Do not make the operator infer which loadout is active from the prompt or generated files.

Also use `references/desktop-visible-launch-checklist.md` for the concrete desktop-terminal attach and verification checklist. Detached tmux alone does not satisfy this workflow.

Minimum notice:

```text
Launching Claude Code: runtime=claude, loadout=<name>, session=<tmux-session>, repo=<path>, permissions=bypass
```

## Procedure

1. Start fresh. Do not reuse an existing Claude Code session unless the operator explicitly asks to resume.
2. Before sending work to Claude Code or Codex, structure the operator prompt. Do not forward the operator's raw shorthand if it leaves repo/path/build target ambiguous. First identify:
   - repo path / working directory
   - runtime (`claude` or `codex`)
   - selected loadout
   - exact build task and deliverable
   - files or areas likely involved
   - verification commands to run
   - constraints such as no deploy, no migration, no force-push, or commit/push expectations

   Prompt shape to send:

```text
Context: You are working in <repo path> on <project>. Current branch: <branch>.
Task: <specific implementation objective>.
Scope: <files/areas to inspect or modify>. Do not change <out-of-scope areas>.
Requirements:
- <requirement 1>
- <requirement 2>
Verification:
- Run <command 1>
- Run <command 2>
Deliverable: Implement the change, verify it with the commands above, and report changed files plus observed test/build output. Commit/push only if instructed.
```

3. Resolve the loadout before launch.
   - If the operator gave an explicit loadout, use that.
   - If the request begins with a slash command, treat the slash command as an invocation wrapper, not the task category. Strip general slash commands such as `/goal`, `/plan`, `/verify`, `/review`, `/run`, `/help`, `/compact`, and `/clear` before routing unless that slash command is explicitly mapped to a loadout.
   - If a slash command is loadout-specific, use its mapped loadout. Example shape: `/frontend-design ...` routes to `frontend-design`; `/research ...` routes to `research`.
   - Otherwise resolve from the cleaned request text with the loadout repo when available:

```bash
cd /home/<operator>/projects/<GITHUB_REPO_NAME>
python scripts/resolve_route.py --runtime claude --request '<cleaned request text>'
```

3. Read or verify the selected loadout from a simple file-backed skill/manifest. Preferred operator-readable shape:

```bash
/home/<operator>/projects/<GITHUB_REPO_NAME>/loadouts/<loadout>/LOADOUT.md
```

Fallback source of truth if that file does not exist:

```bash
/home/<operator>/projects/<GITHUB_REPO_NAME>/loadouts/<loadout>/loadout.yaml
```

The `LOADOUT.md` should read like a Hermes skill: name, when to use it, runtime posture, important commands/files, and what it changes. The first line or frontmatter must include the loadout name so I can report it directly after reading the file.

4. Announce the runtime/loadout in normal prose before launch or as the launch completion line. Mention the file I read, e.g. `read loadouts/default/LOADOUT.md` or `read loadouts/default/loadout.yaml`.
5. Launch via `coding-terminal-loadout-system` (`run_loaded_agent.py --runtime claude --loadout <name> --repo <path> --task-file <enhanced-prompt> --bypass-permissions --watch`); the managed runner must provide desktop-window proof plus tmux client state. A detached tmux session or attached PTY without desktop-window IDs is not considered visible for the operator — verify `visible_terminal_proof.status == desktop_window` before claiming it is visible to them.
6. Diagnostics-only fallback: handling the bypass warning dialog by hand (Down then Enter) applies only to raw diagnostic sessions; the managed runner handles dialogs.
7. Diagnostics-only fallback: capturing the tmux pane by hand to verify visibility applies only to raw diagnostic sessions; managed runs get visibility proof from the runner/watcher evidence.
8. The launch is only reportable as done when the Done-means-done checklist in `coding-terminal-loadout-system` passes — watcher terminal state, structured closeout, verified report routing, and a recorded postback/continuation decision for Discord-origin runs; closeout alone is not done.

## Simple file-backed enhancement

For a low-code UI/status path, write one small JSON status file per launch, for example:

```json
{
  "runtime": "claude",
  "loadout": "default",
  "tmux_session": "claude-<short-name>",
  "repo": "/path/to/repo",
  "permissions": "bypass",
  "launched_at": "ISO-8601 timestamp",
  "request": "short request summary"
}
```

Recommended path:

```bash
/home/<operator>/.hermes/profiles/gateway/run-status/claude-code/<session>.json
```

A future dashboard can read these files and pair them with `tmux capture-pane` output. Tailscale can expose that dashboard privately.

## Failure rule

Do not report a slash command or loadout failed from lack of visible output alone. Only report failure when Claude Code or the loadout resolver returns an explicit error. If the pane is stuck, waiting on permissions, or input was not submitted, fix the tmux/TUI path first.
