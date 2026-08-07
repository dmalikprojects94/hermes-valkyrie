# Interactive launch validation notes

Use this when the remaining question is not auth or plumbing but whether Claude Code and Codex feel correct through the integrated Hermes launch path.

## What counts as a durable pass

For `terminal_agent` / `hermes loadout launch`, verify these in order:

1. The integrated launcher itself succeeds — not just the raw CLI.
2. The visible launch notice shows the intended runtime and resolved loadout.
3. The session lands in the intended repo/workdir.
4. `HOME=/home/<operator>` is preserved for both runtimes.
5. For Codex managed-home launches, `CODEX_HOME` points at the applied Codex runtime home.
6. The interactive session accepts input after startup gates are cleared.

If those pass, the integration is usually correct even if Hermes's process bridge does not capture a clean final reply from the fullscreen TUI.

## Claude-specific note

Interactive repo launches may stop at the trust gate:

`Yes, I trust this folder`

Clear that before judging whether the launcher is broken.

## Recommended reporting language

If the startup path is good but the bridge does not capture the final TUI answer, report it as:

- plumbing/integration: passed
- interactive startup and prompt-entry: passed
- final fullscreen-TUI answer capture through Hermes bridge: limited / requires human-visible terminal verification

Do not collapse those into a generic failure.
