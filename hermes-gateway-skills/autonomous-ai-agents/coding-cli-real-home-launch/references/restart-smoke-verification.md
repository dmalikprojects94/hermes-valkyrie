# Restart Smoke Verification for Hermes Loadout Integration

Use this when the loadout surface was integrated into Hermes and you need to prove it survives a gateway restart.

## Why

A live gateway session may be prevented from restarting its own parent process. On this setup, `hermes gateway restart` from inside the gateway can be refused as loop protection. That is not a product failure; it means restart verification must be triggered externally.

## Recommended pattern

1. Write a detached smoke script under the gateway profile output area.
2. Force `HOME=/home/<operator>` inside the script.
3. Restart the user service with `systemctl --user restart hermes-gateway-gateway.service`.
4. Wait for `systemctl --user is-active --quiet hermes-gateway-gateway.service` to succeed.
5. Run post-restart checks from the Hermes repo:
   - `python -m hermes_cli.main loadout status --json`
   - `python -m hermes_cli.main loadout launch claude --request ... --dry-run --json`
   - `python -m hermes_cli.main loadout launch codex --request ... --dry-run --json`
   - the gateway repo's own CLI test suite for the loadout CLI and terminal-agent tool (gateway development checkout)
6. Log everything to a stable file under `~/.hermes/profiles/gateway/cron/output/`.
7. Trigger the smoke script out-of-band with `systemd-run --user --collect ...` so the current session can disconnect safely while the restart completes.

## Minimal script shape

```bash
#!/usr/bin/env bash
set -euo pipefail

export HOME=/home/<operator>
HERMES_REPO="/home/<operator>/.hermes/hermes-agent"
PYTHON_BIN="$HERMES_REPO/venv/bin/python"
LOG_DIR="$HOME/.hermes/profiles/gateway/cron/output"
LOG_FILE="$LOG_DIR/loadout-restart-smoke.log"

mkdir -p "$LOG_DIR"
exec > >(tee "$LOG_FILE") 2>&1

systemctl --user restart hermes-gateway-gateway.service
for _ in $(seq 1 30); do
  if systemctl --user is-active --quiet hermes-gateway-gateway.service; then
    break
  fi
  sleep 1
done

cd "$HERMES_REPO"
"$PYTHON_BIN" -m hermes_cli.main loadout status --json
"$PYTHON_BIN" -m hermes_cli.main loadout launch claude --request "Use Claude Code for sustained implementation work in this repo" --dry-run --json
"$PYTHON_BIN" -m hermes_cli.main loadout launch codex --request "Use Codex to audit this repo" --dry-run --json
# Gateway development checkout only: run the gateway repo's own CLI test suite
# for the loadout CLI and terminal-agent tool from inside that checkout.
```

## Verification target

The deliverable is not just a successful pre-restart dry-run. The deliverable is a log showing that, after a real service restart, Hermes still exposes the integrated loadout surface and both runtime dry-runs still resolve correctly.
