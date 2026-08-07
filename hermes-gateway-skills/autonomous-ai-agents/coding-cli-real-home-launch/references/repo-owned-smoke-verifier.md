# Repo-Owned Smoke Verifier for Hermes Loadout Launchers

Use this when a Claude/Codex loadout integration is no longer just being debugged manually and needs a repeatable operator check.

## Goal

Create a repo-owned verification script that can be run after a gateway restart, before merge, or after launcher changes. It should exercise the real integrated path rather than only raw CLI commands.

## What the verifier should cover

1. Dry-run integrated launch for both runtimes.
2. Live integrated launch for both runtimes when safe.
3. Returned metadata fields such as `applied_loadout` and `launch_notice`.
4. The user-visible runtime/loadout rendering path, not just raw subprocess success.
5. A simple success sentinel from each runtime so failures are obvious.

## Acceptance shape

A good verifier proves all of these at once:

- Claude integrated launch resolves the correct auth/home context.
- Codex integrated launch resolves the correct auth/home context.
- The selected loadout name is preserved through the adapter metadata.
- Hermes still renders the runtime plus loadout label in operator-visible output.
- The script is safe to re-run from the repo and suitable for CI or pre-merge smoke use.

## Operator handoff

When the engineering work is done, give the operator a very short exact checklist derived from the verifier rather than a long freeform testing brief.
