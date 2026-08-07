# Desktop-visible Claude launch checklist

Use this when applying a Claude loadout and launching a visible Claude Code session.

1. Resolve and announce runtime, loadout, repo, session name, and permissions.
2. Launch Claude Code inside tmux with `HOME=/home/<operator>` and the selected loadout/runtime flags.
3. Attach a real desktop terminal to the tmux session. Detached tmux alone is not visible.
4. Verify the viewer with `tmux list-clients -t <session>` before reporting success.
5. If the viewer command fails, fall back to `xterm -T 'Claude Code - <session> - <repo>' -e bash -lc 'export HOME=/home/<operator>; tmux attach-session -t <session>'`.
6. Keep the viewer attached until the run finishes or the operator explicitly says visibility is no longer needed.

Proof line to capture in the launch report:

```text
/dev/pts/<n>: <session> [<size> xterm] (attached,focused,UTF-8)
```
