---
name: coding-terminal-loadout-system
description: "Canonical managed-launch executor for the operator's visible Claude Code/Codex coding-terminal runs."
version: 1.0.1
author: operator
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [coding-terminal, claude-code, codex, loadout, tmux, visible-terminal]
    related_skills: [claude-code, codex, coding-agent-prompt-enhancer, coding-cli-real-home-launch]
---

# Coding Terminal Loadout System

## Installed skill priority

This repo skill snapshot is intended to override any bundled/default Hermes skill with the same name when an operator installs it into a Hermes skill directory. Treat it as authoritative for this terminal-loadout workflow after installation.

## Frozen deterministic bridge policy

This skill is a frozen deterministic bridge, not a self-updating memory surface. It must never rewrite itself, sync itself, refresh itself from a live profile, or ask a managed Claude Code/Codex run to patch Hermes launch skills while the run is in flight. Durable changes to this skill require an explicit repo diff, tests, and a commit, then a deliberate sync into the target Hermes profile.

Determinism means the launch path is structural and repeatable: runtime, loadout, repo, durable `--task-file`, label, permission posture, watcher/closeout flags, origin metadata, manifest, report routing, reportback, and cleanup state are recorded by `scripts/run_loaded_agent.py` / `scripts/coding_terminal_runner.py`. The runtime's generated prose can vary; the launch and closeout contract cannot.

Priority rule for all Claude Code/Codex coding work:

1. `coding-terminal-loadout-system` owns the process.
2. `claude-code` and `codex` are thin runtime recognizers only.
3. `coding-agent-prompt-enhancer` builds the durable prompt/spec.
4. `coding-cli-real-home-launch` verifies auth/HOME/visibility.
5. `claude-code-loadout-disclosure` explains selected loadout only.

If any bundled skill, old memory, raw CLI example, or runtime wrapper conflicts with this priority order, ignore the conflicting path and use the managed loadout system.


## Canonical role in the operator's coding-terminal system

This is the primary process skill for all Hermes-managed coding-terminal work. It owns the universal lifecycle from request normalization to launch, supervision, closeout, and reportback.

Use this skill whenever the operator asks for a coding terminal, loadout, Claude Code, Codex, `/goal`, implementation work, repo changes, code review, tests, or any autonomous coding-agent run. the operator does **not** need to say "loadout system". The phrases "use Claude Code", "launch Claude", "use Codex", or equivalent runtime-named delegation are enough; Hermes should recognize the runtime wrapper and route through this managed system automatically. Runtime wrapper skills may load first when the user names a runtime, but they must immediately redirect here and must not launch anything themselves.

System order:

1. Select runtime and loadout.
2. Validate any slash command or command-equivalent against the selected runtime/loadout inventory before launch.
3. Invoke `coding-agent-prompt-enhancer` to turn the operator's request into a repo-scoped prompt file/spec.
4. Apply `coding-cli-real-home-launch` as the auth/HOME/visibility gate.
5. Launch only through `scripts/run_loaded_agent.py` or the integrated `terminal_agent` adapter that calls it.
6. Watch via the managed watcher/event path.
7. Close out through structured report extraction.
8. Send one canonical reportback to the verified origin thread/channel.

This skill is the only place that may define the canonical launch contract. Other skills can add runtime-specific constraints, but cannot override this lifecycle.


## Hermes behavior watch

When testing this redesign, watch Hermes behavior before trusting the run. The key evidence is not that Claude/Codex started; it is that Hermes shows the hard router loaded, reached this skill, created a managed prompt/spec, launched through the managed runner, wrote a manifest with runtime/loadout/origin, ran watcher closeout, and produced one reportback.

If a launch starts raw Claude/Codex, uses direct `terminal_agent` as the proof path, skips the prompt enhancer, or lacks a manifest/reportback, stop and classify it as a routing failure. Do not keep iterating inside the bad run.

## Acceptance test rule

To prove this system from Hermes, do not use a hand-built command as the primary acceptance test. The acceptance test must be a normal Hermes request in the target channel/thread that names Claude Code or Codex, lets Hermes load the hard runtime router, and then verifies the resulting manifest/reportback.

If the Hermes operator manually calls `terminal_agent` with a preselected runtime/loadout, that only tests the adapter. It does not prove skill routing. Label it adapter smoke, not full system proof.

The next real acceptance test after skill changes is: restart/reload Hermes, open or use another chat/thread, ask in normal language for Claude Code or Codex to run a tiny repo task, and verify the run reached `coding-terminal-loadout-system`, not raw runtime or direct adapter path.

## Required launch contract

The deterministic input/output contract must be structural and recorded. Short version: Hermes builds a `RunRequest` before launch, the runner writes a manifest and transport evidence, the watcher records terminal/runtime completion, closeout extracts a structured report, routing verifies report artifacts, and reportback-aware runs record exactly one postback/continuation decision.

Deterministic does **not** mean Claude/Codex text is identical every time. It means the run is auditable from recorded state instead of inferred from terminal scrollback or chat prose.

Deterministic inputs are:

- verbatim user request;
- structural origin metadata, never pasted into prompt prose;
- target repo/branch;
- runtime/loadout plus selection reason;
- slash-command intent and source;
- approval mode;
- terminal visibility expectation and reason;
- prompt/spec path;
- expected result packet shape.

Deterministic outputs are:

- manifest/request id;
- input transport proof;
- watcher result;
- structured closeout status/report path;
- raw/project report routing proof;
- Discord postback or explicit blocker state;
- lifecycle state;
- git status/commit state when repo changes happened.

For non-trivial work, create or use a durable prompt file under the target repo, then launch with:

```bash
python /home/<operator>/projects/<GITHUB_REPO_NAME>/scripts/run_loaded_agent.py \
  --runtime <claude|codex> \
  --loadout <resolved-loadout-or-default> \
  --repo <target-repo> \
  --task-file <enhanced-prompt-file> \
  --label <deterministic-session-label> \
  --bypass-permissions \
  --watch \
  --stop-after-closeout \
  --watch-seconds <seconds> \
  --json \
  [--goal "<standing completion condition for Claude only>"] \
  [--discord-guild-id ... --discord-channel-id ... --discord-thread-id ... --discord-thread-name ...]
```

This exact command family is the launch contract for both Claude Code and Codex. Hermes/`terminal_agent` may fill the values, but it must not substitute `--task <raw prompt>`, `--apply-live`, raw runtime CLIs, or missing watcher/closeout flags. A run that does not match this command family is mislaunched; stop it and relaunch correctly.

For Claude Code `/goal` requests, also pass:

```bash
--goal "<standing completion condition>"
```

The runner must submit `/goal <condition>` as the first Claude command and submit the detailed task prompt second. Never use `/gold`; never treat `/goal` as a loadout name; never send bare `/goal`.

For Discord-origin launches, origin IDs are launch metadata only. They must be passed as explicit `--discord-*` flags by `terminal_agent`/runner from session context; do not paste guild/channel/thread IDs into the prompt text.

## One-reportback rule

The desired user-facing completion surface is one canonical structured reportback per managed run. Internal report, continuation review, manager ledger rows, and raw runtime reports may be written to disk, but Discord/Slack should receive one concise final message unless there is a separate explicit blocker or user-visible question.

Canonical reportback must include: outcome, runtime/loadout, changed files, verification result, commit/push status, report path, and blocker/next-step if any.

After a successful Discord-origin postback, the closeout/reportback process should also record a continuation signal for Hermes. Do not depend on Hermes noticing its own Discord notification. The signal should point Hermes at the saved manifest/report and ask it to continue the originating conversation from that evidence. Keep this as a separate continuation lane from `postback_status` so the notification and the follow-up analysis are each idempotent.

Continuation review prompt shape:

```text
Review the completed managed Claude Code/Codex run from the manifest/report paths. Continue the originating Hermes conversation: what did the run complete, what evidence proves it, what did we learn, what changed in project state, and what should happen next? Recommend the next safe step, or ask one concise question if the operator needs to decide. Do not expose secrets, raw IDs, or noisy terminal transcript text.
```

## Done means done

A run is not done when the terminal stops, when Claude/Codex waits for input, or when a closeout file exists. Done means: prompt transport succeeded, watcher observed terminal/runtime completion, no active subagents remain, structured closeout/report exists, report path is readable, git state is understood, and the origin thread/channel received exactly one canonical reportback or an explicit blocked/needs-review message.


Use this skill as the canonical managed-launch executor after Hermes has selected a runtime or after a runtime wrapper has handed off a Claude Code/Codex request. This skill owns the managed loadout/terminal lifecycle; it is not the first-load skill for explicit runtime-named requests.

Runtime-named skills remain the operator-facing front door: `claude-code` for Claude Code requests and `codex` for Codex requests. Those wrapper skills must hand managed execution here instead of re-specifying launch logic or launching raw CLIs.

## Trigger phrases

Primary trigger rule: the operator should never have to ask for the loadout system by name. This is the default, most efficient Hermes launch path for Claude Code and Codex. If they say to use Claude Code, Claude, Codex, a Claude model, `/goal` in Claude Code, or a Codex run, that runtime-named request implies this system.

Load this skill directly for generic managed-executor requests like:

- "use the coding terminal system"
- "run this through the terminal loadout"
- "managed coding terminal"
- "use the loadout system"
- "coding terminal"
- "visible managed coding terminal"

For explicit runtime-named requests, load the wrapper first, then this skill:

- "launch Claude Code" → `claude-code` → this skill with `runtime=claude`
- "visible Claude terminal" → `claude-code` → this skill with `runtime=claude`
- "use `/goal` in Claude Code" → `claude-code` → this skill with `runtime=claude`
- "send this to Codex" → `codex` → this skill with `runtime=codex`

If the operator asks for ordinary shell execution, do not force this path. Use it when they want an autonomous coding runtime or explicit loadout behavior.

## Canonical repo and command path

The source-of-truth repo is:

```text
/home/<operator>/projects/<GITHUB_REPO_NAME>
```

Use this runner for live coding-agent sessions:

```bash
python scripts/run_loaded_agent.py \
  --runtime claude \
  --loadout default \
  --repo <target-repo> \
  --task-file <enhanced-prompt-file> \
  --label <short-label> \
  --bypass-permissions \
  --watch \
  --stop-after-closeout \
  --watch-seconds <seconds> \
  --json
```

For Codex, use `--runtime codex` and the selected loadout.

Hard routing rule: Hermes MUST route all managed Claude Code and Codex coding-agent work through this repo-managed TMUX/loadout system via `scripts/run_loaded_agent.py`. NEVER launch raw `claude`, raw `codex`, or ad-hoc tmux sessions for delegated work. Raw CLI use outside the runtime wrappers' Diagnostics gate is a routing violation to report, not a fallback. Fresh Codex runs should pass the managed prompt as the startup prompt (`input_transport: initial_prompt`) instead of relying on post-launch multiline paste/send into the TUI.

For Discord-origin launches, append the explicit origin flags (`--discord-guild-id --discord-channel-id --discord-thread-id --discord-thread-name`) and export `HOME=/home/<operator>` plus `SAVE_DESTINATION_PATH=/path/to/save-destination` (or the legacy `OBSIDIAN_VAULT_PATH` alias) in the launch environment.

## Runtime wrapper contract

`claude-code` and `codex` are runtime wrappers. They decide runtime-specific constraints, then invoke this skill for managed execution. They may append runtime-specific requirements, but they must not override the core managed-launch rules in this skill.

Decision rule:

- If the operator explicitly names Claude Code or Claude, load `claude-code` first, then route managed execution here with `runtime=claude`.
- If the operator explicitly names Codex, load `codex` first, then route managed execution here with `runtime=codex`.
- If the operator asks generically for a managed coding terminal/loadout system, this skill may be loaded directly after Hermes chooses or confirms the runtime.
- If the task is only an auth/version/native-event-shape diagnostic, the wrapper may use raw CLI commands and must report that no managed execution proof was produced.

Wrappers should provide or derive these inputs before launch:

- chosen runtime: `claude` or `codex`
- target repo/path
- task text or enhanced prompt source
- explicit loadout, if the operator named one
- visibility preference, defaulting to visible for the operator
- slash-command or command-equivalent requirements
- resume/new-session intent
- runtime-specific constraints such as Claude `/goal` handling, Claude model/status verification, Codex git-repo/auth requirements, or Codex event/hook expectations
- diagnostic-only flag when the wrapper intentionally does not invoke the managed executor

Managed closeout should report these outputs/evidence:

- manifest path
- runtime and loadout used
- desktop-window proof plus tmux session/client evidence when visibility was requested
- prompt transport and watcher/runtime-event state
- latest report path and artifact routing information
- final `doctor` or `operator-status` proof when lifecycle state matters

See `docs/hermes-skill-routing-contract.md` for the durable three-layer routing contract.

## Required preflight

1. Resolve the target repo/path yourself. Do not ask the operator if it can be found locally.
2. Load/use `coding-agent-prompt-enhancer` before sending the task to the runtime.
3. Run the Mandatory launch gate from `coding-cli-real-home-launch`: `HOME=/home/<operator> claude auth status --text` (Claude) or `HOME=/home/<operator> codex --version` plus auth presence (Codex). If the preflight fails, STOP — do not launch; report the auth blocker to the operator with the exact failing command and output.
4. For normal managed Claude/Codex launches, `--bypass-permissions` is mandatory and the runner must record `permission_posture: managed_bypass_required`. If the repo/task is unsafe for bypass, do not start a standard managed launch in approval mode; stop and ask the operator whether to use an explicitly manual/diagnostic non-managed path or change scope. State the chosen posture in the launch notice and final report.
5. Use the real user home for standalone coding CLIs. On this machine the real home is:

```text
/home/<operator>
```

6. Keep the terminal visible by default. `--no-visible` is only for explicit opt-out or narrow CI-style diagnostics. Auto-close successful structured closeouts by default with `--stop-after-closeout`; use `--keep-open-after-closeout` only when the operator explicitly asks to inspect, verify live terminal behavior, or keep the session open for follow-up.
7. Prefer fresh sessions for major workstreams.
8. Do not use ACP for Claude Code on this setup.
9. Do not bypass this runner with raw `claude` or `codex` commands unless the task is a narrow CLI diagnostic; ordinary coding-agent delegation must stay inside the managed TMUX/loadout lifecycle.

## Source provenance and loadout onboarding

When the operator provides a promising GitHub repo, GitHub star list, Claude Code pack, Codex pack, prompt pack, skill pack, hook pack, or runtime-config bundle to integrate into the loadout system, use the source-accounting process in `references/loadout-source-provenance-onboarding.md`. That reference covers the generic source-list registry/tool pattern: save reusable list access as data, but keep executable helpers list-agnostic so the operator's `Claude Stack` list is just one alias, not hard-coded logic.

When the operator asks to keep going down the loadout-source project without needing them, use `references/queue-driven-source-ingestion.md`: treat the saved source list as a work queue, run one source-accounted classification report per repo, update the source matrix / queue doc / the maintainer source registry (not shipped publicly), verify, and only then decide whether a separate migration micro-pass is warranted. Do not migrate runtime material during the classification pass.

When the operator asks to develop an onboarding command, audit an entire repo/star-list queue, synthesize hypothesis loadouts, or feed a braindump into Claude Code `/plan` for this source-ingestion system, use `references/source-list-onboarding-command-system.md`. Prefer extending the maintainer source-registry tooling (not shipped publicly) into a registry/state-backed command surface over writing one-off prompt-only workflows; keep JSON state canonical, render Markdown artifacts from it, and separate audit/synthesis/migration planning from actual materialization.

When the operator frames the problem as GitHub digestion, skill onboarding, or deciding whether a source has functionality worth adding, use `references/loadout-github-digestion-backlog-design.md`. The critical lesson is that upstream analysis is untrustworthy until the repo has a local loadout functionality audit/capability matrix: every loadout's commands, hooks, skills, agents, adapters, MCP surfaces, generated files, provenance, and Claude/Codex parity must be knowable before duplication/conflict decisions are made. Recommendation output must be actionable for file-adding workflows: distinguish evidence (`target_loadouts` / inherited memberships) from edit destinations (`proposed_targets` / `files_to_touch`), naming the exact loadout or repo area, target surface, proposed files, and reason before claiming something is ready to onboard.

When comparison/admission output touches adapter-only, runtime-specific-adapter, source/catalog/provenance, or process-only candidates, use `references/source-comparison-adapter-process-routing.md`. Do not route that work through `loadout-management` as a fake implementation target. Emit `adapter/process` or `target_loadout: null`, suppress `loadout-management` from human-facing implementation suggestions, and keep useful-but-already-covered items as explicit no-implementation audit signals.

For source-comparison/disposition audits, also use `references/loadout-source-comparison-disposition.md`. Important boundary: useful upstream material is not automatically an implementation target. Preserve `already-covered`/`repo-resident-reference` rows as audit evidence with `no-implementation`, route adapter/process/parity work outside runtime loadout additions, and do not make `loadout-management` a catch-all target for onboarding results.

When the operator asks to fully migrate, solidify, or stabilize the `default` loadout before working on other loadouts, use `references/default-loadout-solidification.md`. Treat `default` as the inherited backbone: backfill provenance on every default frame file, verify both Claude and Codex materialization, document the status in the repo, and keep bulky/specialty behavior out unless it passes the loadout-builder admission rule.

The short rule for new sources: inventory the upstream repo, classify every meaningful item, distill shared intent into `shared/`, map it into Claude Code and Codex as evenly as practical, document any intentional runtime gaps, update the maintainer source matrix, and add per-frame provenance for source-derived files. For classification-only passes, explicitly record that net runtime materialization was `0` and defer adoption to a later micro-pass.

Do not call a loadout synchronized just because Claude and Codex both support the loadout name. Synchronization means equivalent user-facing behavior or a documented intentional gap.

## Slash-command and command-inventory verification feature

When the operator includes a slash command such as `/goal`, `/plan`, `/review`, `/context-budget`, or asks what commands are available:

1. Do not assume the command exists just because it sounds valid.
2. First check the repo-bound inventory for the selected runtime/loadout:
   - `python scripts/list_runtime_commands.py --runtime claude --loadout <loadout>`
   - `python scripts/list_runtime_commands.py --runtime codex --loadout <loadout>`
   - after `apply_loadout`, inspect the generated `command-inventory.json` and `command-inventory.md` in the runtime home.
3. Treat command inventory as a per-loadout invariant. the operator wants one slash-command/command-equivalent inventory surface for every loadout, not just the default loadout. If a loadout is added or changed, update and verify the inventory for that loadout in the same workflow.
4. Keep durable operator docs current in the loadout repo, especially `docs/claude-code-installed-capabilities.md`, `docs/codex-installed-capabilities.md`, and any generated runtime inventory docs. See `references/runtime-command-inventory-maintenance.md` for the maintenance pattern and pitfalls.
5. Claude Code slash commands are repo materialized from `adapters/claude/commands/<name>.md` and the selected loadout's `runtime_overrides.claude.commands`. The default inheritance chain includes `/command-inventory` to check the active list from inside Claude.
6. Codex native slash commands are tracked in `adapters/codex/commands.yaml`; Hermes-managed command equivalents are exposed as Codex skills and listed in the generated `hermes-command-inventory` skill and `docs/codex-installed-capabilities.md`.
7. If uncertain, verify before relying on it. Acceptable checks:
   - inspect the command file/registry above;
   - inspect the selected `loadouts/<name>/loadout.yaml` to confirm it is active;
   - use live runtime startup evidence when the question is about native runtime-owned commands rather than repo-provided commands.
8. If the command is unavailable in the selected loadout, either switch to a loadout that includes it or convert the request into a normal natural-language prompt. State the choice briefly.
9. For Codex planning requests where the operator says `/plan`, verify inventory first. If Codex does not expose native `/plan`, use the `project-planner` loadout and explicitly frame the task as the `/plan` equivalent: planning/design mode, repo-aware documentation updates, no implementation beyond requested docs. See `references/codex-planning-runs.md`.
10. For Claude Code `/goal`, never send bare `/goal` as the first line. Send `/goal <standing completion condition>` as one submitted command line, then send the detailed prompt as a normal follow-up.
11. When the operator specifies an exact Claude model for a visible `/goal` run, verify the live TUI banner/status first. If the requested model is already active, that is sufficient proof even if `/model <name>` rejects the display alias; do not treat the alias rejection as failure. See `references/claude-goal-model-verification.md`.
12. Only claim a slash command worked if the live runtime accepted it or the repo/inventory surface proves it is installed and the run completed through closeout.

Command inventory is a launch gate, not a nice-to-have. Treat runtime command handling as three classes:

- **Global runtime commands**: available in the runtime/default inheritance chain; keep the current/default loadout unless another routing signal is stronger.
- **Loadout-scoped commands**: commands or command-equivalent skills that appear only in a specific loadout's inventory. If the operator invokes one, select that loadout or block clearly if the requested runtime cannot support it.
- **Unknown commands**: do not invent a loadout or silently pass them through. Normalize only obvious typos with a documented alias rule, otherwise ask or convert to a natural-language prompt with the uncertainty stated.

The prompt enhancer is mandatory after command validation. Final rule: once runtime, loadout, command intent, repo, permission posture, and origin are known, push the request through `coding-agent-prompt-enhancer` / `scripts/prompt_manager.py` before launch unless the operator explicitly asks for a raw diagnostic. Prompt management stays lean: preserve the operator's original request, write/store a durable task prompt, add only repo/loadout/verification/reportback constraints, and keep routing IDs out of prompt prose.

## Prompt shape

Write an enhanced prompt to a temp file before launch. Include:

```text
Context: target repo/path, current branch, runtime/loadout.
Original request: the operator's words.
Task: concrete objective.
Scope: likely files/areas; explicit out-of-scope.
Requirements: visible/runtime constraints, slash-command handling, safety rules.
Verification: exact commands the runtime should run.
Deliverable: changed files, verification output, blockers, and git status. After the watcher finishes, review and commit obvious essential durable source/docs/tests/prompts locally; do not commit ambiguous/raw artifacts, and do not push unless instructed.
```

## Runtime monitoring, closeout, and session lifecycle

Watcher-with-closeout is not "should" — it is the default launch shape. Every managed launch MUST run with `--watch` (or `watch-start --closeout-on-complete --postback-on-closeout --postback-transport auto`). A run without a watcher is a misconfigured run: fix and relaunch or attach a watcher before doing anything else. Do not make tmux pane/status polling the default completion signal. The watcher path means a finished Claude/Codex run closes out, updates the durable run ledger, and posts exactly once back to the verified Discord thread. See `docs/reportback-system.md` for the reportback contract and `references/session-lifecycle-and-report-routing.md` for the detailed operator checklist when sessions remain open, closeout behavior is ambiguous, or report routing needs to be verified. For true Claude Code `/goal` slash-command runs, use `references/claude-goal-raw-command-lifecycle.md` so `/goal` is submitted as a raw command instead of embedded inside the managed prompt wrapper; this is also the pattern for pushing a whole multi-phase roadmap into Claude Code as a live, persistent goal-loop. If the operator says to "push/send this to Claude Code" after a plan/prompt exists, do not hand back instructions for them to do it themselves; launch the managed visible Claude session, submit the raw `/goal` line, then submit the follow-up execution prompt and report proof. See `references/live-managed-audit-closeout-proof.md` for the concrete live-smoke proof pattern: visible Claude/Codex managed runs, structured closeout, runtime-specific save-destination/project report copies, auto-stop evidence, final `doctor ok`, and the two known diagnostic-polish edges. See `references/goal-closeout-and-operator-hardening.md` for lessons from hardening `/goal` closeout parsing, operator-status normalization, and safe cleanup behavior. See `references/codex-parity-and-smoke-verification.md` when the operator asks to do the same workflow with Codex, audit Claude/Codex command parity, or verify watcher/report routing with mock plus live golden-path tests. See `references/paired-claude-codex-visible-doc-runs.md` when the operator asks to run Claude Code and Codex visibly in parallel to document/audit loadout functionality.

### 30-second supervision cadence and context hygiene

When a Claude/Codex run is actively working, supervise it in short 30-second wait/poll loops. Avoid long opaque sleeps such as 120/180/240 seconds, because they delay the operator summary and make Discord feel stale. Do not use `notify_on_complete=true` for managed Claude/Codex runs that emit large JSON closeout payloads into Discord; that creates raw background-process bursts in chat. Start the bounded background process silently, retain the `session_id`, poll/wait from the Hermes operator, and post only concise summarized status/closeout. After each 30-second interval, re-check the manifest/status/report path and, if the runtime has produced a meaningful response, summarize it back to the current Discord message thread before continuing deeper work. If the work is likely to span multiple polling cycles, refresh or compact the active context early: capture the manifest path, tmux session, repo, branch, prompt/report paths, current git status, and next expected signal so the closeout owner can resume cleanly after compaction or restart.

The rest of this section describes the optional Hermes gateway integration (the `terminal_agent` tool and gateway session metadata); it applies when launches originate from a Hermes gateway. Before launching a delegated Claude/Codex run, check the operator surface with `operator-status --json`. The runner also re-checks after safe stopped-session cleanup and blocks new non-resume launches when the requested runtime has reached the default active-session limit of 10 managed coding-terminals, when active sessions cannot be classified by runtime, or when needs-attention, runtime-event-failed, or orphan coding-terminal sessions remain; pass `--allow-open-sessions` only as an explicit override. Claude and Codex each have their own runtime lane, so up to 10 active Claude sessions and up to 10 active Codex sessions may run concurrently when the machine/API budget can handle it. For Discord-originated launches, the origin is carried automatically as launch metadata: session context → the `terminal_agent` tool → explicit `--discord-guild-id`, `--discord-channel-id`, `--discord-thread-id`, and `--discord-thread-name` flags on `run_loaded_agent.py`. The `terminal_agent` tool builds those explicit flags from session context (`HERMES_SESSION_SCOPE_ID` / `HERMES_SESSION_PARENT_CHAT_ID` / `HERMES_SESSION_THREAD_ID` / `HERMES_SESSION_CHAT_NAME`) and hard-errors when the Discord origin is incomplete: a Discord-origin managed launch with incomplete origin now fails loudly at launch with a refusal naming the missing ids, instead of silently parking as `needs_origin_review`. Routing IDs (guild/channel/thread) must NEVER be pasted into prompt text — they are launch metadata only. Env-only origin (no explicit flags) remains audit-only and never auto-posts. the Hermes operator should resolve the human thread name and pass it when available. After the run, check operator status again. If sessions remain open, report exactly which lifecycle state they are in and why they were not closed; do not let stale sessions accumulate silently.

When validating report routing from a gateway or non-interactive shell, do not assume the save-destination env is inherited. If `doctor` reports artifact fallback for raw/project reports but a configured save destination exists, rerun the preflight and live smokes with `SAVE_DESTINATION_PATH=/path/to/save-destination` (or the legacy `OBSIDIAN_VAULT_PATH` alias) exported inline, then require `doctor` to show `status: ok`, runtime-specific raw roots under `agents/claude-code/raw-runs` or `agents/codex/raw-runs`, project roots under `projects/<project-slug>/artifacts/coding-terminal-runs`, and no warnings before calling routing healthy.

When syncing gateway-profile skills from this repo into an active Hermes profile, keep backup copies outside any `skills/` subtree. A backup directory inside `~/.hermes/profiles/<profile>/skills/` can be scanned as if it were a real skill category and pollute `hermes skills list`. Use a sibling such as `~/.hermes/profiles/<profile>/backups/<backup-name>` and then verify with `hermes --profile <profile> skills list` that the skills resolve from `autonomous-ai-agents`, not from the backup path.

For watched one-shot delegated runs, the raw managed runner should auto-stop after a successful structured closeout with no blockers unless the operator explicitly asks to inspect the visible terminal. The Hermes `terminal_agent` tool default is auto-stop / `--stop-after-closeout`; pass `--keep-open-after-closeout` only for explicit inspection or live behavior verification. When asked to review a terminal run, first check `operator-status`/`cleanup-stopped`; if a finished run is `terminal_response_state=ready_to_close` or `stopped_safe`, close it with managed cleanup instead of leaving it open.

Healthy closeout evidence usually includes:

- `visible: true`
- an attached tmux client under `clients`
- prompt transport proof (`input_transport: initial_prompt` for fresh Codex runs, or a recorded `last_prompt_id` for post-start sends)
- `runtime_event_hook.configured == true`; for Codex this should show `transport: codex_cli_override`, a `hooks.Stop` CLI override, and `--dangerously-bypass-hook-trust` in the launch command
- `watcher_status` running after prompt send/startup injection
- `closeout.status == "structured"` when complete
- `latest_report` path
- `watcher_wait.result.watch_result == "terminal_state"`

Closeout is report extraction/routing; it is not the same as closing the tmux session. The conservative lifecycle policy is:

- redact every persisted report, summary, and provenance copy;
- auto-close only after structured closeout with no blockers;
- start every new `send`/fresh Codex startup as a new tracked turn and clear stale runtime events, closeout paths, watcher result files, and report pointers;
- when a managed `send` happens while a watcher is active, terminate the old watcher and restart a new watcher for the new turn; otherwise the old watcher can keep writing to an unlinked result file and the session will finish with `waiting_for_input`, `watcher_status: not_running`, and `closeout_status: not_run`;
- bind runtime Stop events to the current prompt id/start time so a later closeout cannot reuse a previous run’s final report;
- classify missing final messages, malformed watcher output, partial watcher results, or vanished blocked/failed terminals as `needs_attention`;
- surface runtime-event recording failures in `operator-status` instead of silently ignoring `.events.failed.jsonl` files;
- keep blocker detection narrow and section-aware so prose like “fixed the failed test” does not mark a run blocked;
- resolve the runtime HOME from `HERMES_REAL_HOME`/`REAL_HOME`, falling back to `/home/<operator>`, and confirm the resolved value in `operator-status`.

For one-shot delegated runs where the operator expects the session to disappear after successful completion, add:

```bash
--stop-after-closeout
```

That flag only stops the session after structured closeout with no blockers. It intentionally leaves blocked, failed, malformed-watcher, unstructured, or `no_final_message` sessions open for inspection.

New coding-terminal runs preflight-clean stopped sessions by default before starting a fresh non-resume run. Leave this enabled unless you are deliberately preserving a stopped terminal for inspection. The cleanup path must never close active work: `cleanup-stopped` only targets live tmux sessions whose lifecycle is `stopped` and `auto_cleanup_safe == true`.

Use `doctor` first for the plain-English health decision, then `operator-status` for current/open operator state, `orphans list` / `orphans cleanup` for unmanaged tmux sessions, `reports list` for artifact discovery, and narrower list commands if you need to drill into a state. Human/default output must be readable and decision-oriented; preserve full audit detail behind `--json`. Do not make the default human operator view a historical run archive. See `references/operator-human-output-and-history-boundary.md` for the human-vs-JSON formatting boundary and the rule that raw handoff/work artifacts are still allowed, but historical run tracking is not default.

```bash
python scripts/coding_terminal_runner.py doctor --repo /home/<operator>/projects/<GITHUB_REPO_NAME> --json
python scripts/coding_terminal_runner.py operator-status --repo /home/<operator>/projects/<GITHUB_REPO_NAME> --json
python scripts/coding_terminal_runner.py orphans list --repo /home/<operator>/projects/<GITHUB_REPO_NAME> --json
python scripts/coding_terminal_runner.py orphans cleanup --repo /home/<operator>/projects/<GITHUB_REPO_NAME> --yes --json
python scripts/coding_terminal_runner.py reports list --repo /home/<operator>/projects/<GITHUB_REPO_NAME> --json
python scripts/coding_terminal_runner.py reports repair --repo /home/<operator>/projects/<GITHUB_REPO_NAME> --json
python scripts/coding_terminal_runner.py list --repo /home/<operator>/projects/<GITHUB_REPO_NAME> --json
python scripts/coding_terminal_runner.py list --repo /home/<operator>/projects/<GITHUB_REPO_NAME> --open-only --json
python scripts/coding_terminal_runner.py list --repo /home/<operator>/projects/<GITHUB_REPO_NAME> --state active --json
python scripts/coding_terminal_runner.py list --repo /home/<operator>/projects/<GITHUB_REPO_NAME> --state stopped --json
```

`doctor` should be the operator-facing answer to “is this system healthy?” It reports active/stopped/needs-attention/orphan sessions, route preflight, missing routed report copies, and recommended cleanup/repair actions.

`reports list` should be the answer to “where did the files go?” It reports local closeout report, raw Obsidian report/summary, project mirror report/summary, existence checks, and any missing copies. `reports repair` may backfill missing Obsidian/raw or project copies from surviving local/project/raw report files; it redacts copied text and does not create a new model-authored report.

Lifecycle states are intentionally distinct:

- `active`: watcher running or status `starting`, `ready`, or `working`; never auto-clean.
- `stopped`: tmux exists, watcher is not running, and status is `waiting_for_input`, `finished`, or `stale`; safe cleanup target.
- `needs_attention`: tmux exists and status is `blocked` or `failed`; leave open.
- `closed`: tmux does not exist; no cleanup needed.

Run the safe cleanup explicitly with:

```bash
python scripts/coding_terminal_runner.py cleanup-stopped --repo /home/<operator>/projects/<GITHUB_REPO_NAME> --json
```

Close a specific completed session explicitly with:

```bash
python scripts/coding_terminal_runner.py stop --manifest <manifest.json> --json
```

If closeout fails, inspect the manifest, events JSONL, watcher log, and report paths before declaring failure.

Raw/project artifact route contract:

- `raw_path`: the runtime raw lane. This is the always-valid memory-vault capture lane for Claude Code/Codex output.
- `project_path`: the organized project lane. Use it when the run clearly fits the current target project; otherwise leave the artifact in `raw_path` and report why project placement did not fit.

Keep this contract in the prompt enhancer and routing metadata, not in repo `CLAUDE.md`, so individual projects do not accumulate prompt bloat. Runtime-specific raw paths should resolve to `$SAVE_DESTINATION_PATH/agents/claude-code/raw-runs/` for Claude Code and `$SAVE_DESTINATION_PATH/agents/codex/raw-runs/` for Codex. Project paths should resolve to `$SAVE_DESTINATION_PATH/projects/<project-slug>/artifacts/coding-terminal-runs/`. If the save destination is missing, the router falls back to local artifact paths and surfaces that in `doctor`/`operator-status`. Legacy internal aliases `raw_root`, `project_root`, and `sorted_path` may remain for compatibility, but user/operator language should prefer `raw_path` and `project_path`. For the detailed bug pattern, repair flow, and verification checklist, use `references/obsidian-project-artifact-routing.md`.

## Test and save-destination environment isolation

The loadout runner writes raw runtime reports to the configured save destination when `SAVE_DESTINATION_PATH` (or the legacy `OBSIDIAN_VAULT_PATH` alias) is set. That is correct for live runs, but test helpers and subprocess-based fixtures must not inherit the live save-destination path. In test harnesses, explicitly remove these variables before launching subprocesses that create fixture repos or project slugs, then verify the suite does not create generic paths such as `$SAVE_DESTINATION_PATH/projects/repo/`. If such a path appears, quarantine it outside the save destination first, inspect it for fake/test content, fix the environment leak, rerun the full tests, and only then refresh recovery-seed artifacts if any durable real files changed.

## Git and artifact rules

After a Claude/Codex watcher finishes, always review and prepare the resulting repo changes before reporting done:

1. Run `git status --short` and inspect the diff for every changed or untracked tracked-intent file.
2. Separate durable source/docs/tests/prompts from raw runtime artifacts. Never stage raw artifacts just because they were produced during the run.
3. If the changed files are clearly essential to the completed request — for example source fixes, tests, durable docs, audit records, or repo-owned prompt packets that explain/reproduce the run — stage and commit them locally without asking again.
4. If the diff includes ambiguous, broad, risky, secret-bearing, or unrelated edits, do not commit those parts. Restore or leave them clearly reported for the operator’s decision.
5. After any commit, re-check `git status --short` and report commit hash plus push status. Do not push unless the operator explicitly asked for push or the repo workflow requires it.

Commit only requested/important source, docs, tests, loadout changes, and repo-owned prompt/audit artifacts that are essential to the completed work.

Do not commit raw run artifacts:

- local runtime terminal artifacts
- local project report mirrors
- local planning scratch artifacts
- local prompt scratch artifacts
- `.claude/`
- `.codex/`
- `output/`

The repo `.gitignore` should already exclude these paths. If they appear, fix ignore rules rather than committing them.

## Verification commands

Before reporting a repo/system change as done, run at least:

```bash
python scripts/validate_loadouts.py
python scripts/smoke_clean_hermes_onboarding.py --json
```

For narrow documentation-only changes, `python scripts/validate_loadouts.py` plus direct file existence/content checks may be enough, but say what was skipped.

## Done-means-done

A managed coding-agent run may be reported complete ONLY when all of:

1. `watcher_wait.result.watch_result == "terminal_state"` — the event-driven watcher, not tmux capture, observed the finish.
2. `closeout.status == "structured"` with the five-heading report extracted; blockers field inspected (a blocked run is reported as blocked, never as done).
3. Report routing verified: raw report under `$SAVE_DESTINATION_PATH/agents/<claude-code|codex>/raw-runs/…` and project mirror under `projects/<slug>/artifacts/coding-terminal-runs/…` exist (`reports list` or closeout JSON paths checked).
4. Reportback verified for Discord-origin runs: `postback_status: posted` and manager/continuation state accounted for (`continued`, `awaiting_continuation_decision` with the operator notified, or an explicit `needs_origin_review`/`failed` reported as a blocker). Non-Discord runs: state that no postback lane applies.
5. Git reviewed: `git status --short` inspected; essential durable files committed per the existing git/artifact rules; raw artifacts left untracked; commit hash + push status reported.
6. Lifecycle clean: session auto-stopped after clean structured closeout, or its open state and reason reported; `operator-status`/`doctor` shows no new needs-attention/orphan/failed-postback state caused by this run.
7. Report delivered in the five-heading shape with the evidence above, including runtime/loadout used and permission posture.

If any item fails, the run is "not done": report the failing item as a blocker with the exact command output. Closeout alone is NOT done — a managed Discord-origin run also requires watcher terminal state, verified report routing, and a recorded postback/continuation decision (posted, or an explicit blocked/needs-review state reported to the operator).

## Reporting contract

Do not report a run as done unless every Done-means-done item passed; report any failed item as a blocker instead.

Report concise operational status to the operator:

- what runtime/loadout was used;
- whether terminal was visible, backed by desktop-window proof (tmux attachment alone is not enough) when visibility was requested;
- what file(s) changed;
- exact verification output;
- where the raw save-destination report landed and where the project mirror report landed;
- final operator-status session state, especially open/needs-attention/orphan counts;
- commit/push status if requested;
- any raw artifacts intentionally left out.

After visible Claude/Codex documentation or audit runs, inspect `git status` and `git diff` before final reporting. If the agents made incidental broad edits outside the requested deliverables, restore those unrelated edits, rerun validation/tests, and mention the cleanup briefly.
