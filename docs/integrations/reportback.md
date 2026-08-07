# Reportback integration

Reportback is optional. The loadout system can be used entirely from a local shell, but an orchestrator may want to post closeout summaries to a chat thread, file log, dashboard, or ticket. This page defines the portable reportback contract without assuming any private transport.

## Lifecycle

```text
launch request
    │
    ▼
materialize loadout surface
    │
    ▼
runtime executes task
    │
    ▼
agent closeout: changes, evidence, blockers, next steps
    │
    ▼
transport: file log, chat thread, dashboard, or ticket
```

## Minimum closeout shape

A useful reportback includes:

- task summary;
- runtime and loadout used;
- files changed or generated;
- commands run and actual outputs;
- unresolved blockers or risks;
- next action required from the operator;
- watcher/closeout status when a managed runtime launch was used;
- visible desktop-window proof when the operator expected to watch the terminal.

## Environment-only transport configuration

Transport settings belong in environment variables or `.env`, not tracked files. For Discord-style reportback, use placeholders such as:

```bash
DISCORD_BOT_TOKEN=<your-bot-token>
DISCORD_GUILD_ID=<guild-id>
DISCORD_CHANNEL_ID=<channel-id>
DISCORD_THREAD_ID=<thread-id>
DISCORD_THREAD_NAME=<thread-name>
```

Use your own target IDs. Never publish real IDs or credentials in docs, tests, loadout files, or generated public examples.

## Test locally first

Before enabling live transport, write to a local file log or sandbox output and inspect the closeout:

```bash
mkdir -p output/reportback
cat > output/reportback/example-closeout.md <<'EOF'
# Example closeout
Runtime: claude
Loadout: research
Evidence: python scripts/validate_loadouts.py -> loadouts valid
Transport: file_log
EOF
```

Only switch to live transport after the operator approves the destination.

## Managed-launch reportback status

For managed Claude Code/Codex launches, do not collapse all states into
"success" or "failure." Preserve the exact state:

| State | Meaning |
| --- | --- |
| `posted` | Closeout was delivered to the configured destination. |
| `skipped` | Reportback was intentionally disabled or not configured. |
| `needs_origin_review` | The run completed but the destination metadata was incomplete. |
| `failed` | Transport was attempted and failed. |

A local closeout file plus missing reportback metadata should be reported as
`needs_origin_review`, not as a silent success.


## Terminal closeout policy

Managed terminal cleanup is a separate policy decision from report extraction. A portable implementation should keep one auditable policy for whether finished terminals auto-close after reportback.

Recommended states:

| State | Cleanup behavior |
| --- | --- |
| `awaiting_response` | Keep open; reportback has not been recorded yet. |
| `ready_to_close` | Eligible for auto-close if policy allows it. |
| `kept_for_inspection` | Leave open intentionally; manual cleanup may close later. |
| `blocked_or_failed` | Leave open for review. |
| `active_or_unknown` | Leave open; never guess. |

The policy should be recorded with the run manifest/reportback metadata so an operator can answer why a terminal closed or stayed open.

## Privacy rules

- Do not include service credentials in report text.
- Do not include private chat IDs in public docs.
- Do not include operator names or private machine paths.
- Prefer generic labels such as `operator`, `workspace`, and `runtime home`.

## Related docs

- [Environment Configuration](../guides/environment-configuration.md)
- [Running Under an Orchestrator](hermes.md)
