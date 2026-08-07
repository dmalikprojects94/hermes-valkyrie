# Delegation Policy

Decide before acting: handle inline, or delegate to a subagent.

## Handle inline when

- The task is local, fast, and reversible.
- One or two files, one or two tools, one or two verification steps.
- You already have enough context loaded to act without re-reading the repo.
- The work is a bug fix, surgical edit, doc tweak, or single-step verification.

## Delegate to a subagent when

- The task is multi-step exploration: "find all X across the repo and report Y."
- The work would otherwise pollute the main context with raw tool output (large grep dumps, file walks, log sweeps).
- The task is independent enough to be briefed standalone, with a self-contained prompt.
- A specialty agent already exists for this lane (code-reviewer, security-reviewer, docs-lookup, build-error-resolver, performance-optimizer, tdd-guide, planner, harness-optimizer, silent-failure-hunter, code-architect).

## Brief subagents like cold colleagues

- State the goal and the why, not just the steps.
- Hand over file paths, line numbers, and concrete artifacts.
- Cap response length when the answer is meant to be short.
- Never delegate the *synthesis* — own the final decision and the wiring back into the change.

## Anti-patterns

- Spawning an agent for a single grep that would have been one tool call.
- Asking an agent to "decide what to do" instead of asking it to gather facts.
- Running multiple agents that overlap heavily; prefer one well-briefed agent.
- Treating an agent's report as proof of the change — verify the actual diff.

## Parallelism

When agents are independent, dispatch them in one batch. When the second agent depends on the first agent's findings, run sequentially.

## Provenance

- Source: local Claude-OC-System default backbone doctrine plus internal Hermes-operator adaptation.
- Disposition: distilled-into-default.
- Notes: migrated as lean shared instruction text so Claude Code and Codex can inherit the same default intent.
