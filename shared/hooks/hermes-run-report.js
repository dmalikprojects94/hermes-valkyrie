#!/usr/bin/env node
/**
 * hermes-run-report.js
 *
 * Stop hook. Reads the harness Stop-event payload from stdin and, when
 * HERMES_RUN_REPORT_PATH is set, appends a structured run-report record so
 * Hermes can pick up a post-run artifact.
 *
 * No-op unless HERMES_RUN_REPORT_PATH points at a writable file path.
 * Cross-platform: uses fs and path only. Exits 0 unconditionally.
 *
 * Environment:
 *   HERMES_RUN_REPORT_PATH - absolute path to a JSONL file. If unset, the hook
 *                            silently exits.
 *   HERMES_LOADOUT         - active loadout name (optional, recorded if set).
 *   HERMES_RUNTIME         - active runtime name (optional, recorded if set).
 */

"use strict";

const fs = require("fs");
const path = require("path");

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

function safeParse(raw) {
  if (!raw || !raw.trim()) return null;
  try {
    return JSON.parse(raw);
  } catch (_) {
    return null;
  }
}

function parseReportSections(summary) {
  if (!summary || typeof summary !== "string") return null;
  const headings = ["Request", "Changes", "Verification", "Blockers", "Next Steps"];
  const escaped = headings.map((heading) => heading.replace(/[-/\\^$*+?.()|[\]{}]/g, "\\$&"));
  const pattern = new RegExp(`^##\\s+(${escaped.join("|")})\\s*$`, "gim");
  const matches = [...summary.matchAll(pattern)];
  if (!matches.length) return null;

  const sections = {};
  for (let i = 0; i < matches.length; i += 1) {
    const current = matches[i];
    const next = matches[i + 1];
    const heading = current[1];
    const start = current.index + current[0].length;
    const end = next ? next.index : summary.length;
    sections[heading.toLowerCase().replace(/\s+/g, "_")] = summary.slice(start, end).trim() || null;
  }
  return sections;
}

async function main() {
  const target = process.env.HERMES_RUN_REPORT_PATH;
  if (!target) {
    process.exit(0);
    return;
  }

  const raw = await readStdin();
  const payload = safeParse(raw);
  const summary = payload && payload.summary ? payload.summary : null;
  const sections = parseReportSections(summary);

  const record = {
    hook: "hermes-run-report",
    timestamp: new Date().toISOString(),
    loadout: process.env.HERMES_LOADOUT || null,
    runtime: process.env.HERMES_RUNTIME || null,
    event: payload && payload.event ? payload.event : "Stop",
    session: payload && payload.session ? payload.session : null,
    summary,
    sections,
  };

  try {
    const dir = path.dirname(target);
    if (dir && !fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    fs.appendFileSync(target, JSON.stringify(record) + "\n", { encoding: "utf8" });
  } catch (_) {
    // Hook stays a no-op on any write error.
  }

  process.exit(0);
}

main().catch(() => process.exit(0));

/*
Provenance
- Source: local Claude-OC-System default hook pattern, adapted for Hermes.
- Disposition: runtime-specific-adapter for Claude Code default.
- Notes: renamed and parameterized for Hermes rather than OpenClaw runtime state.
*/
