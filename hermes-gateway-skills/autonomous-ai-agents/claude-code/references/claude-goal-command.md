# Claude Code `/goal` command note

Session learning: in Claude Code v2.x, submitting bare `/goal` opens/shows goal status (`No goal set` / status panel). It does not start a standing goal.

Reliable pattern for goal-driven runs:

```text
/goal <complete standing goal condition in one line>
```

Then submit a normal follow-up prompt that points Claude at the detailed execution packet and tells it to begin.

Example:

```text
/goal Complete the remaining implementation in /path/to/repo by following agent-prompts/GOAL_PACKET.md; continue until required verification passes and final report includes changed files plus real command output, or stop only on a concrete blocker.
```

Follow-up prompt:

```text
Read `agent-prompts/GOAL_PACKET.md` now and execute it. Start by inspecting repository state and existing uncommitted changes; preserve them unless intentionally incorporating or superseding them. Run required verification and report only real results.
```

Do not put `/goal` alone as the first line of a prompt file and assume Claude Code will treat the rest of the file as the goal condition. The condition must be on the submitted `/goal` command line.