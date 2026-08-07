# tmux-backed visible Claude input in this environment

Use this when Claude Code must stay visible on-screen but Hermes also needs to drive prompts reliably.

## Why this exists

On this setup, direct Hermes PTY/process input into fullscreen Claude can mangle prompt text before Claude receives it. The same Claude launch can still work if input is delivered through `tmux send-keys` instead of `process submit/write`.

This is a transport workaround, not a repo-code change.

## Working pattern

1. Force the real home:
   - `export HOME=/home/<operator>`
2. Start Claude inside tmux in the target repo:
   - `tmux new-session -d -s claudeproof -x 120 -y 40 'cd /target/repo && claude --append-system-prompt-file /target/repo/output/claude/CLAUDE.md'`
3. Verify startup by capturing the pane:
   - `tmux capture-pane -pt claudeproof | tail -40`
4. If the operator wants visible proof, attach that tmux session inside a real desktop terminal window:
   - `xterm -T 'Claude TMUX Visible' -e bash -lc 'tmux attach -t claudeproof'`
5. Drive Claude through tmux, not Hermes PTY writes:
   - plain prompt: `tmux send-keys -t claudeproof 'Say hello in one sentence.' Enter`
   - slash command: `tmux send-keys -t claudeproof '/goal status' Enter`
6. Re-capture the pane after each send:
   - `tmux capture-pane -pt claudeproof | tail -120`

## Acceptance bar

Only claim success if the tmux pane shows the exact intended prompt or slash command, not a distorted variant.

Good proof shape:
- visible startup banner in the right repo
- exact prompt echoed in the pane
- Claude reply shown in the pane
- for slash commands, explicit `/goal` status/output such as `Goal set:` or `◎ /goal active`

## Important boundaries

- Do not treat repo code as the problem if the same launch works once input moves to tmux.
- Do not conclude that Claude slash commands are broken if the failure only occurs through Hermes PTY/process writes.
- This pattern is for interactive verification. For one-shot non-interactive work, normal CLI print/exec modes may still be simpler.
