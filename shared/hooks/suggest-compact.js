#!/usr/bin/env node
/**
 * suggest-compact.js
 *
 * PreToolUse hook. Reads the harness event payload from stdin and emits a
 * compact-suggestion message when the session's context-token usage crosses
 * a configurable warning band.
 *
 * Cross-platform: no Windows-specific paths, no shell calls. Reads stdin and
 * writes JSON or plain text to stdout. Exits 0 unconditionally so it never
 * blocks the underlying tool call.
 *
 * Environment:
 *   HERMES_COMPACT_LOWER  - lower band as percent (default: 35)
 *   HERMES_COMPACT_UPPER  - upper band as percent (default: 55)
 */

"use strict";

const LOWER = parseFloat(process.env.HERMES_COMPACT_LOWER || "35");
const UPPER = parseFloat(process.env.HERMES_COMPACT_UPPER || "55");

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

function extractUsagePercent(payload) {
  if (!payload || typeof payload !== "object") return null;
  const candidates = [
    payload.context_usage_percent,
    payload.context_percent,
    payload.session && payload.session.context_usage_percent,
    payload.session && payload.session.context_percent,
  ];
  for (const value of candidates) {
    if (typeof value === "number" && Number.isFinite(value)) {
      return value > 1 ? value : value * 100;
    }
  }
  return null;
}

async function main() {
  const raw = await readStdin();
  let payload = null;
  if (raw && raw.trim()) {
    try {
      payload = JSON.parse(raw);
    } catch (_) {
      payload = null;
    }
  }

  const percent = extractUsagePercent(payload);
  if (percent === null) {
    process.exit(0);
    return;
  }

  if (percent < LOWER) {
    process.exit(0);
    return;
  }

  const severity = percent >= UPPER ? "high" : "warn";
  const suggestion = {
    hook: "suggest-compact",
    severity,
    context_percent: Math.round(percent * 10) / 10,
    band: { lower: LOWER, upper: UPPER },
    message:
      severity === "high"
        ? "Context usage is high. Consider /compact or a fresh session before continuing."
        : "Context usage is climbing. /compact soon to keep headroom.",
  };
  process.stdout.write(JSON.stringify(suggestion) + "\n");
  process.exit(0);
}

main().catch(() => process.exit(0));

/*
Provenance
- Source: local Claude-OC-System default hook pattern, adapted for Hermes.
- Disposition: runtime-specific-adapter for Claude Code default.
- Notes: renamed and parameterized for Hermes rather than OpenClaw runtime state.
*/
