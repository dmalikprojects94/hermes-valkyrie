#!/usr/bin/env node
/**
 * pre-bash-dev-server-block.js
 *
 * PreToolUse hook. For frontend-oriented loadouts: prevents the runtime from
 * launching long-running dev servers in the foreground when the operator has
 * not opted in. Reads the harness payload from stdin and emits a block
 * decision when the command pattern matches a known dev-server invocation.
 *
 * Cross-platform: no Windows-specific paths. Exits 0 normally; exits 1 with a
 * JSON decision payload when blocking.
 *
 * Environment:
 *   HERMES_ALLOW_DEV_SERVER - when set to a truthy value, hook is a no-op.
 */

"use strict";

const ALLOW = (() => {
  const value = process.env.HERMES_ALLOW_DEV_SERVER;
  if (!value) return false;
  return ["1", "true", "yes", "on"].includes(value.toLowerCase());
})();

const BLOCKED_PATTERNS = [
  /\bnpm\s+(run\s+)?dev\b/,
  /\bpnpm\s+(run\s+)?dev\b/,
  /\byarn\s+(run\s+)?dev\b/,
  /\bnpm\s+(run\s+)?start\b/,
  /\bvite\b/,
  /\bnext\s+dev\b/,
  /\bremix\s+dev\b/,
  /\bastro\s+dev\b/,
];

function readStdin() {
  return new Promise((resolve) => {
    let data = "";
    if (process.stdin.isTTY) {
      resolve("");
      return;
    }
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (chunk) => {
      data += chunk;
    });
    process.stdin.on("end", () => resolve(data));
    process.stdin.on("error", () => resolve(data));
  });
}

function extractCommand(payload) {
  if (!payload || typeof payload !== "object") return null;
  if (payload.tool_input && typeof payload.tool_input.command === "string") {
    return payload.tool_input.command;
  }
  if (typeof payload.command === "string") return payload.command;
  return null;
}

async function main() {
  if (ALLOW) {
    process.exit(0);
    return;
  }
  const raw = await readStdin();
  let payload = null;
  if (raw && raw.trim()) {
    try {
      payload = JSON.parse(raw);
    } catch (_) {
      payload = null;
    }
  }

  const command = extractCommand(payload);
  if (!command) {
    process.exit(0);
    return;
  }

  for (const pattern of BLOCKED_PATTERNS) {
    if (pattern.test(command)) {
      const message = {
        hook: "pre-bash-dev-server-block",
        decision: "block",
        reason:
          "Foreground dev-server commands are blocked. Run them in the background, or set HERMES_ALLOW_DEV_SERVER=1 to opt in.",
        matched: pattern.source,
      };
      process.stdout.write(JSON.stringify(message) + "\n");
      process.exit(1);
      return;
    }
  }

  process.exit(0);
}

main().catch(() => process.exit(0));
