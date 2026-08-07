# Hermes Gateway Coding-Terminal Skills

This directory is the versioned Hermes skill control plane for the Terminal Loadout System.

These skills are not generic, self-growing memory. They are deterministic bridge skills: Hermes loads them, they decide how to call the deterministic scripts and adapters in this repo, and the scripts/adapters do the repeatable work.

## Why these skills are in the repo

The loadouts and adapters explain what a terminal runtime should receive. The Hermes skills explain when and how Hermes should call those deterministic pieces.

```text
Hermes skill loaded in a session
    │
    ▼
choose managed workflow / slash-command behavior
    │
    ▼
scripts/run_loaded_agent.py or related deterministic script
    │
    ▼
loadouts/<name>/loadout.yaml + shared/ intent
    │
    ▼
adapters/claude or adapters/codex materialization
    │
    ▼
Claude Code or Codex terminal run
    │
    ▼
watcher + closeout + reportback
```

Without this folder, the public repo would show the loadouts and adapters but not the Hermes-facing skills that actually cause Hermes to call them.

## Update policy

These snapshots are frozen/deterministic by default.

They must not self-update from inside a managed coding-terminal run. Do not treat them like ambient learned skills that a running agent patches whenever it discovers something. Changes require a reviewed repo diff, tests, and a commit.

Growth happens through explicit surfaces:

- reviewed slash-command behavior;
- new or changed loadouts;
- new shared skills or packs;
- deterministic adapter updates;
- source-accounted ingestion commits.

The useful model is: **flat bridge skills, growing setup/loadout library**.

## Tracked skills

- `coding-terminal-loadout-system` — canonical managed tmux/loadout workflow, watcher lifecycle, closeout, routing, git/artifact rules.
- `coding-agent-prompt-enhancer` — prompt shaping before delegating work to Claude Code/Codex/OpenCode.
- `coding-cli-real-home-launch` — real-home/auth launch rules for standalone Claude/Codex CLIs from Hermes.
- `claude-code-loadout-disclosure` — visible Claude launch disclosure and desktop attach expectations.
- `claude-code` — Claude Code operating guide used by Hermes.
- `codex` — Codex CLI operating guide used by Hermes.

## Sync checklist

1. Confirm the change is intentional and belongs in deterministic gateway-skill behavior.
2. Copy the full skill directory into `hermes-gateway-skills/autonomous-ai-agents/`.
3. Update `manifest.json` if the tracked skill set or update policy changes.
4. Update public docs if the workflow impact changed.
5. Run `python scripts/validate_loadouts.py` and `python scripts/smoke_clean_hermes_onboarding.py --json`.
6. Commit the skill snapshot with the related loadout-system change.

Do not put raw run artifacts here. This is durable skill source and references only.
