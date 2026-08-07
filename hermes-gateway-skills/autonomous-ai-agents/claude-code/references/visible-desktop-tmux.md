# Visible desktop tmux requirement for the operator

Use this when launching or auditing Claude Code sessions for the operator.

## Rule

A detached tmux session is only the control plane. It does **not** satisfy the operator's visibility requirement by itself. Unless the operator explicitly opts out, every Claude Code run must also have a real desktop terminal window attached to the tmux session.

## Launch/attach pattern

Start Claude in tmux with the real user HOME:

```bash
tmux new-session -d -s <session> -x 160 -y 48 "cd <repo> && HOME=/home/<operator> claude --dangerously-skip-permissions --model sonnet --effort high"
```

Then open a desktop-visible viewer attached to the same tmux session:

```bash
xterm -T 'Claude Code - <session> - <repo-name>' -e bash -lc 'export HOME=/home/<operator>; tmux attach-session -t <session>'
```

If a preferred GNOME terminal command is available and known-good, it can be used instead. If a `kgx` command is shadowed by another CLI or does not support normal terminal flags, fall back to `xterm` rather than treating the launch as visible.

## Verification

Before reporting that Claude Code is visible, run:

```bash
tmux list-clients -t <session>
```

Expected proof shape:

```text
/dev/pts/<n>: <session> [<cols>x<rows> xterm] (attached,focused,UTF-8)
```

Also check the process surface if needed:

```bash
pgrep -af "xterm.*<session>|tmux attach-session -t <session>|claude --dangerously"
```

## Pitfalls

- Do not say a run is visible just because `tmux list-sessions` shows it exists.
- Do not rely on hidden background Claude or print-mode runs when the user is specifically asking to observe Claude Code behavior.
- If the gateway restarts, re-check both `tmux list-sessions` and `tmux list-clients`; a tmux session may survive while the desktop viewer is gone, or both may be lost.
- Keep the terminal attached for the full run unless the operator says they do not need to watch it.
