# Claude `/goal` model verification

Session learning from a visible Claude Code `/goal` planning run:

- the operator requested Opus 4.8 explicitly.
- The visible Claude Code TUI banner showed `Opus 4.8 (1M context) · Claude Max`, which is valid model proof.
- Sending `/model opus 4.8` returned `Model 'opus 4.8' not found`, even though the banner already confirmed the requested model was active. Treat that as a display-alias mismatch, not a model failure.
- Correct sequence for this class of run:
  1. Launch the managed visible Claude terminal through the loadout runner.
  2. Verify the attached desktop client and inspect the TUI banner/status for the requested model.
  3. If the requested model is already active, proceed without forcing `/model`.
  4. Send `/goal <complete standing condition>` as its own submitted command.
  5. Confirm the TUI says `Goal set:`.
  6. Send the enhanced detailed prompt as the follow-up task.
  7. Use runtime-event watcher/closeout and route the structured report.

Do not report a `/model` alias rejection as a blocker when the live banner proves the requested model is active.
