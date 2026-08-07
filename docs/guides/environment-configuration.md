# Environment configuration

The public system should run with no required `.env` file for inspect-only and sandbox materialization. Environment variables are for optional personalization and live integrations, not for making basic validation work.

## Design principle

Keep defaults portable and safe:

- validation works from a clean clone;
- sandbox output writes under `output/` unless a command says otherwise;
- live runtime homes require explicit operator approval;
- optional integrations are disabled when their variables are unset;
- secrets live in environment variables or an untracked `.env`, never in tracked docs or loadouts.

## Setup modes

| Mode | `.env` needed? | Variables usually used | Notes |
| --- | --- | --- | --- |
| Inspect-only | No | None | Read docs and run validation. |
| Sandbox materialization | No | None | Generate `output/claude` and `output/codex`. |
| Local capture/reporting | Optional | `SAVE_DESTINATION_PATH`, reportback variables | Use only when the operator wants run artifacts routed to a chosen folder. |
| Live-home setup | Optional | `HOME` only when the launcher uses a nonstandard home | Requires explicit approval. |
| Public release preparation | Optional | `PUBLIC_TARGET_ACCOUNT` | Helps record intended public destination; does not publish by itself. |

## The `.env.example` contract

Copy the template only when you need personalization:

```bash
cp .env.example .env
```

Then either source it in your shell or have your orchestrator load it before invoking scripts. The template is documentation and a safe placeholder file; it is not automatically loaded by every Python script.

## Variables

| Variable | Required? | Used for | Safe default |
| --- | --- | --- | --- |
| `HOME` | No | Runtime home discovery when intentionally overridden. | Shell default. |
| `SAVE_DESTINATION_PATH` | No | Optional durable run capture folder. Can be an Obsidian vault path, a notes folder, or any writable directory. | Unset; `./local-runtime-artifacts/raw-capture/` fallback for wrapper capture, or command-specific local artifact fallback. |
| `OBSIDIAN_VAULT_PATH` | No | Legacy compatibility alias for existing Hermes/Obsidian deployments. | Unset. Prefer `SAVE_DESTINATION_PATH` in public docs and new setups. |
| `DISCORD_BOT_TOKEN` | No | Optional Discord reportback transport. | Unset; no Discord delivery. |
| `DISCORD_GUILD_ID` | No | Optional reportback target. | Unset. |
| `DISCORD_CHANNEL_ID` | No | Optional reportback target. | Unset. |
| `DISCORD_THREAD_ID` | No | Optional reportback target. | Unset. |
| `DISCORD_THREAD_NAME` | No | Optional human label for reportback. | Unset. |
| `PUBLIC_TARGET_ACCOUNT` | No | Intended account/org for a future extracted public repo. | Unset. |

### Advanced and orchestrator-supplied variables

These are read by the shipped scripts but are normally unset for standalone use.
An orchestrator (such as a Hermes gateway) supplies them per run.

| Variable | Used for | Safe default |
| --- | --- | --- |
| `HERMES_CLAUDE_MODEL` / `CLAUDE_CODE_MODEL` | Override the pinned Claude Code launch model ID. | Unset; managed launches pin the documented default. |
| `HERMES_CODEX_MODEL` / `CODEX_MODEL` | Override the Codex launch model. | Unset. |
| `HERMES_REAL_HOME` / `REAL_HOME` | Point runtime-home discovery at the real user home when `HOME` is sandboxed. | Unset; `$HOME` is used. |
| `HERMES_HOME`, `HERMES_PROFILE`, `HERMES_PROFILE_NAME`, `HERMES_ACTIVE_PROFILE` | Locate an orchestrator profile home for bridge-skill installs and smoke tests. | Unset; standalone runs do not need a gateway profile. |
| `HERMES_MANAGED_LAUNCHER`, `HERMES_CODING_TERMINAL_VISIBLE`, `HERMES_ENV_FILE` | Managed-launch behavior flags set by the orchestrator wrapper. | Unset. |
| `HERMES_SESSION_*` (session/thread/channel/guild IDs, titles, goal/request text) | Origin and reportback metadata attached to a managed run by the orchestrator. | Unset; runs are anonymous/local. |
| `HERMES_TERMINAL_COMPLETION_WEBHOOK_URL` / `HERMES_TERMINAL_COMPLETION_WEBHOOK_SECRET` | Optional completion webhook (URL plus HMAC secret) fired at closeout. Secret material — env-only, never committed. | Unset; no webhook egress. |
| `HERMES_DEFAULT_OBSIDIAN_VAULT_PATH` | Second legacy alias consulted after `OBSIDIAN_VAULT_PATH`. | Unset. Prefer `SAVE_DESTINATION_PATH`. |

## Loading environment values manually

A POSIX shell can load simple `KEY=value` entries with:

```bash
set -a
. ./.env
set +a
```

Only do this after reviewing the file. Do not source a file from an untrusted location.

## Verification

Check what the current process sees:

```bash
python - <<'PY'
import os
for key in ('SAVE_DESTINATION_PATH', 'DISCORD_GUILD_ID', 'PUBLIC_TARGET_ACCOUNT'):
    print(key, os.environ.get(key, '<unset>'))
PY
```

Do not print secret values in logs. For secret-bearing variables, print only whether they are set.

## Public sharing rule

A public sharing repo should include `.env.example` and `.gitignore`, but not `.env`. The template should contain placeholders only. If a real value is needed to reproduce a run, record the variable name and purpose, not the value.
