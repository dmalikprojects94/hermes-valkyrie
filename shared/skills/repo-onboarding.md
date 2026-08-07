# Repo Onboarding

Lightweight first-touch ingestion. Use at the start of a session when the runtime has not seen this repo before, or has not seen it recently.

## Goal

Build the minimum mental model needed to act competently: where the code lives, how it builds, how it tests, and how it deploys. No deep audit, no exhaustive walkthrough.

## Pipeline

1. **Top-level scan.** Read `README.md`, `CLAUDE.md`, `AGENTS.md`, or any other root-level orientation doc.
2. **Doc-chain check.** If the repo uses a local `AGENTS.md` / `agents.md` hierarchy, map the relevant doc chain before editing and follow it for the rest of the session.
3. **Project shape.** Identify language(s), framework(s), build system, test runner, and package manager from the top-level config files.
4. **Entry points.** Find the main binary, server entry, or library root. One file each.
5. **Test surface.** Locate the test directory and identify the test command. Do not run the full suite; just confirm the command exists.
6. **Local run.** Identify how to start the app or library in dev mode (one command).
7. **Domain hot spots.** Note the 2-4 directories that look like the domain core, not the plumbing.

## Output

A 6-line brief:

- Language / framework
- Build command
- Test command
- Dev run command
- Domain hot spots (max 4 paths)
- Anything surprising about the layout

That brief gets used as session context for the rest of the work.

## What this skill is not

- Not a full architecture review (use `code-architect` for that).
- Not a code audit (use `code-reviewer` or `security-reviewer`).
- Not a planning session (use `/plan` or `project-planner` loadout).
- Heavier multi-pass ingestion belongs in a specialty loadout, not default.

## Provenance

- Source: local Claude-OC-System default skill surface plus internal Hermes-operator adaptation.
- Disposition: distilled-into-default.
- Notes: migrated as a shared runtime-portable skill for the solidified default loadout.
