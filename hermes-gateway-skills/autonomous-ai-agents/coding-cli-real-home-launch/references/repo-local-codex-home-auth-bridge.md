# Repo-local Codex home auth bridge

Use this when a loadout system materializes a repo-local Codex runtime home and launches Codex with that `CODEX_HOME`, while the valid standalone Codex OAuth session already lives in the real user home.

## Trigger

- `codex exec ...` works with `HOME=/home/<operator>` in the repo
- the same task fails after setting `CODEX_HOME` to an applied repo-local output root
- the repo-local launch shows auth failures even though the normal standalone Codex CLI is already logged in

## Durable pattern

Keep both of these true at once:

- `HOME=/home/<operator>` for the real desktop-shell auth context
- `CODEX_HOME=<applied repo-local codex output>` so the generated runtime surface is actually used

If the applied `CODEX_HOME` does not contain Codex auth state, bridge it by linking the auth file from the real Codex home:

```bash
ln -sfn /home/<operator>/.codex/auth.json <applied CODEX_HOME>/auth.json
```

This preserves the repo-local runtime surface while reusing the already-authenticated standalone Codex account.

## Why this is preferred

- avoids copying secrets into a second file
- avoids editing repo source
- keeps the proof honest: Codex is really using the repo-local applied home
- keeps the auth source of truth in the real `~/.codex`

## Verification

1. Launch with:
   - `HOME=/home/<operator>`
   - `CODEX_HOME=<applied repo-local codex output>`
2. Capture the visible PTY with `script` when proof is needed.
3. Confirm the log contains:
   - `CODEX_HOME=<applied repo-local codex output>`
   - `HOME=/home/<operator>`
   - the expected active loadout line
   - a successful Codex startup banner or exit code 0

## Notes

The useful lesson is the bridge pattern, not the original auth failure text. Do not save raw transient 401 strings as a durable rule; save the repo-local-home auth-bridge fix.