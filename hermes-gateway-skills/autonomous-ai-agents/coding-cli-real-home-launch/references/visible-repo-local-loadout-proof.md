# Visible repo-local Claude loadout proof

Use this when the operator wants to see Claude launch on-screen with a repo-local applied loadout, while leaving repo code untouched.

## Goal

Prove all of the following in one run:

- selected runtime is Claude
- selected loadout was applied repo-locally
- Claude launched in a visible desktop terminal
- the launch used the generated repo-local `CLAUDE.md`
- the session came up in the intended repo with repo-code modification explicitly disallowed unless requested

## Recipe

1. Apply the loadout repo-locally and keep the resulting manifest path.
2. Create a small launcher script that:
   - exports `HOME=/home/<operator>`
   - `cd`s into the target repo
   - prints a short prelude with `PWD`, `HOME`, output root, manifest path, and manifest-selected loadout/runtime
   - executes `script -q -f -a <proof-log> -c "... claude --append-system-prompt-file <output-root>/CLAUDE.md ..."`
3. Launch that script in a real desktop terminal, preferably `x-terminal-emulator -T '<title>' -e <script>`.
4. Ask Claude to print exact proof lines first, before any other normal reply content.
5. Report the output root, manifest path, key generated files, and the proof lines from the log.

## Minimal proof prompt shape

Ask Claude to print exact lines for:

- `ACTIVE_LOADOUT=<name>`
- `APPEND_SYSTEM_PROMPT_FILE=<absolute path to repo-local CLAUDE.md>`
- `WORKDIR=<repo path>`
- `REPO_CODE_MODIFICATION=forbidden-unless-explicitly-requested`

Then have it add one short confirmation sentence that the loadout context is active.

## Why this pattern matters

`--append-system-prompt-file` lets Hermes prove a repo-local applied loadout was actually injected into Claude for this session, without rewriting the user's live `~/.claude` home and without changing repo code.

## Evidence to preserve

From the launcher prelude:

- output root
- manifest path
- selected runtime/loadout
- `HOME=/home/<operator>`

From the PTY log:

- the full Claude command including `--append-system-prompt-file`
- the printed proof lines
- the short confirmation sentence
- optional `pgrep -af` output showing the Claude process is still live

## Notes

- `script` output will include ANSI escape sequences; keep the meaningful proof lines anyway.
- Claude may print unrelated startup notices like model availability or auto-update warnings. Those do not invalidate the launch proof if the requested proof lines still appear.
