---
name: coding-agent-prompt-enhancer
description: "Preflight prompt enhancement for Claude Code, Codex, and other visible coding-agent terminals."
version: 1.0.1
author: operator
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [Coding-Agent, Prompting, Claude-Code, Codex, Tmux]
    related_skills: [claude-code, codex, claude-code-loadout-disclosure, coding-cli-real-home-launch]
---

# Coding-Agent Prompt Enhancer

## Installed skill priority

This repo skill snapshot is intended to override any bundled/default Hermes skill with the same name when an operator installs it into a Hermes skill directory. Treat it as authoritative for this terminal-loadout workflow after installation.

Priority rule for all Claude Code/Codex coding work:

1. `coding-terminal-loadout-system` owns the process.
2. `claude-code` and `codex` are thin runtime recognizers only.
3. `coding-agent-prompt-enhancer` builds the durable prompt/spec.
4. `coding-cli-real-home-launch` verifies auth/HOME/visibility.
5. `claude-code-loadout-disclosure` explains selected loadout only.

If any bundled skill, old memory, raw CLI example, or runtime wrapper conflicts with this priority order, ignore the conflicting path and use the managed loadout system.


## Role in the operator's coding-terminal system

This skill is the prompt/spec builder. It turns the operator's shorthand from any channel/thread into a durable, repo-scoped prompt file plus launch metadata for `coding-terminal-loadout-system`.

Prompt management means the prompt the operator sends to Hermes must reach this skill before it reaches Claude Code/Codex, unless the run is an explicit raw diagnostic. The enhancer is the single preflight surface that tightens a user request into the actual coding-agent task packet.

It must not launch Claude or Codex itself. It prepares the handoff packet.

The loadout system should call this after runtime/loadout/command validation. This is prompt management, but it must stay lean: preserve the operator's original request, add the minimum repo-aware execution constraints, write or point to a durable prompt/spec, and return metadata the runner can record. Do not turn every launch into a long planning ceremony.

For every managed coding-agent request, produce or ensure:

- target repo/path and branch
- runtime and loadout choice, or explicit unresolved field
- original user request in plain language
- concrete task objective
- scope and out-of-scope boundaries
- verification commands
- project update instruction check when the task touches GitHub, branches, PRs, releases, public sharing, or repo publication
- commit/push expectation
- slash-command handling: for Claude `/goal`, a non-bare goal condition separate from the task prompt
- command-validation result: whether the slash command is global, loadout-scoped, converted to a runtime equivalent, or blocked before launch
- artifact routing instructions using `raw_path` and `project_path`: `raw_path` is the always-valid capture lane; `project_path` is the organized lane only when the run clearly fits the current project
- reportback shape: one canonical structured reportback
- origin statement as human context only; routing IDs stay launch metadata and never appear in prompt text

For non-trivial work, write the enhanced prompt under an operator-selected local workspace such as `agent-prompts/` or another ignored task-file directory. The runner should receive `--task-file <prompt>` and, for Claude goal-loop work, `--goal "<condition>"` separately.


Use this before sending the operator's request into Claude Code, Codex, or any other coding-agent terminal.

The goal is not to make a long plan. The goal is to convert the operator's shorthand into a repo-aware, terminal-agent-ready prompt that can be pasted into the agent with fewer follow-up questions.

## Trigger

Use when:

- the operator asks to send work to Claude Code, Codex, OpenCode, or an agent terminal.
- the operator gives a broad build/fix/review request that needs repo/path/build-task specificity.
- A slash command like `/goal`, `/plan`, or `/prompt-optimize` appears before an otherwise loose implementation request.

## Source basis

This is based on the existing Claude prompt optimizer surface:

- `/home/<operator>/projects/<GITHUB_REPO_NAME>/shared/skills/prompt-optimizer.md`
- `/home/<operator>/projects/<GITHUB_REPO_NAME>/adapters/claude/commands/prompt-optimize.md`
- `/home/<operator>/projects/<GITHUB_REPO_NAME>/loadouts/claude/Folder-Start/rules/20-prompt-prep-pipeline.md`

## Procedure

1. Preserve the operator's original intent. Do not invent product decisions.
2. Resolve the target repo/path autonomously when possible. Search local projects before asking the operator.
3. Inspect lightweight repo context when needed: `git status`, branch, README/CLAUDE/AGENTS docs, package/build files, and obvious test commands.
4. Resolve runtime/loadout separately. Generic slash commands are not loadout routing signals unless explicitly mapped.
5. If a slash command appears, require a command-inventory check before enhancement. If the command is loadout-scoped, the prompt must record the selected loadout and why. If the command is unavailable, do not enhance/launch as if it were valid; return a blocker or a natural-language conversion note.
6. Capture the route before writing the prompt: Discord origin (thread name / context), target repo path, chosen runtime and loadout, commit/push expectation, and required reportback shape. Enhanced prompts carry task intent only: Discord guild/channel/thread/message IDs are launch metadata (explicit `--discord-*` flags on `run_loaded_agent.py`), never prompt prose — the enhancer neither needs nor receives routing IDs. `/goal` conditions are extracted to launch metadata (`--goal "<condition>"`), not left embedded in the prose.
7. Enhance the prompt with only the details needed for the coding agent to execute well:
   - context: repo path, project, branch
   - task: specific objective
   - scope: likely files/areas to inspect or modify
   - out-of-scope: adjacent work to avoid
   - requirements: concrete behavior constraints
   - verification: exact commands or best-known commands to run
   - deliverable: changed files, test/build output, commit/push instruction if applicable
8. If a missing fact changes the execution path, ask one clarifying question. Otherwise proceed with labeled assumptions.
9. Send the enhanced prompt into the fresh visible tmux-backed agent session. Do not send raw shorthand unless it is already specific.

## Prompt shape

```text
Context: You are working in <repo path> on <project>. Current branch: <branch>.
Runtime/loadout: <runtime> / <loadout>.
Origin: <Discord thread name, or "none/local">. Routing IDs are launch metadata — never included here.
Commit/push: <commit locally | commit+push | report-only>.
Original request: <the operator's request>.
Task: <specific implementation objective>.
Scope: Inspect/modify <files or areas>. Do not change <out-of-scope areas>.
Requirements:
- <requirement 1>
- <requirement 2>
- If this task touches GitHub, branches, PRs, releases, public sharing, or repo publication, check for project update instructions in the repo before editing.
Artifact routing:
- default_path: <save destination root when configured, otherwise fallback stated by the runner>
- raw_path: <runtime raw lane for Claude Code or Codex>
- project_path: <organized project lane when the work clearly fits the current project>
- Treat raw_path as the always-valid capture lane. If the work clearly fits the current project, also use/report project_path; otherwise leave it in raw_path and state why no project placement fit.
Verification:
- <command 1>
- <command 2>
Deliverable: Implement the change, run verification, review the resulting git diff, commit obvious essential durable source/docs/tests/prompts locally, and report changed files plus observed output. Do not commit raw runtime artifacts or ambiguous/unrelated edits; do not push unless instructed.
Reportback: End with the exact five headings Request / Changes / Verification / Blockers / Next Steps, as a markdown report document.
```

## Discipline

- Prompt enhancement is a preflight step, not a separate planning ceremony.
- The operator-facing invariant is: the operator prompt → runtime router → command inventory/loadout check → this enhancer → managed runner. If the prompt skipped this enhancer, the launch path is incomplete.
- Keep it concise; tightening removes ambiguity, it does not add bureaucracy.
- Do not block on perfect knowledge if repo context gives a safe default.
- Do not ask the operator for repo/path if it can be found locally.
- Do not let `/goal` or another generic slash command replace actual repo/task scoping.
- If the operator asks for a Claude `/goal` plan/document, treat the durable prompt file as part of the deliverable: write it under the repo's prompt/docs area, put the complete `/goal <condition>` on the first line, include the detailed implementation spec below it, verify required markers, then launch Claude by submitting the `/goal` line first and a short follow-up pointing Claude at the file.
- For Claude Code goal-loop prompts, do not put bare `/goal` as a standalone first line. Use `/goal <complete standing condition>` on one submitted command line, then submit the detailed prompt as a normal follow-up. For managed runs, extract the condition to `run_loaded_agent.py --goal "<condition>"` rather than embedding it in the prose.
- Route fields are not optional decoration. A prompt that omits origin, repo path, runtime/loadout, verification, commit/push expectation, or reportback shape is not enhanced — it is unrouted. Do not send it.
- Origin must also be passed as explicit `--discord-*` launch flags built from session context by the `terminal_agent` tool; env-derived origin alone is `needs_origin_review` and will not auto-post. Routing IDs never appear in the enhanced prompt text.
- The launched run is only done when the Done-means-done checklist in `coding-terminal-loadout-system` passes, including a recorded postback/continuation decision for Discord-origin runs — closeout alone is not done.
