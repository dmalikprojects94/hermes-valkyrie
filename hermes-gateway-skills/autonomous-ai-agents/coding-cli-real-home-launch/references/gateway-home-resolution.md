# Gateway-home resolution notes

Use this when Hermes runs under a profile sandbox home but Claude/Codex must still launch under the real logged-in user context.

## Durable pattern

- Resolve the real user home in the Hermes adapter layer, not only in operator shell examples.
- Prefer an explicit override knob such as `HERMES_LOADOUT_USER_HOME` for deterministic tests and future deployment changes.
- Derive default loadout-repo and runtime-home paths from the real user home.
- Merge manifest-defined `launch.env` into the actual subprocess environment before launch.
- For Codex, preserve `CODEX_HOME=<applied runtime home>` even when `HOME` is forced to the real user home for auth context.

## Why this matters

A gateway process may legitimately run with a profile sandbox `HOME`, but standalone coding CLIs can keep auth and config under the real desktop user home. If the adapter uses `Path.home()` blindly, `status`, `apply`, `launch`, and tool-level dry-runs can all point at the wrong repo and runtime homes.

## Verification shape

1. Dry-run the Hermes loadout launch surface from inside the live gateway session.
2. Confirm resolved repo/home paths point at the real user locations.
3. Confirm emitted manifest data includes the intended `launch.env`.
4. Run at least one synthetic subprocess launch to prove the child process really sees `HOME`, `CODEX_HOME`, and any extra manifest env keys.
