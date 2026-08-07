# Interactive input integrity check for Claude Code via Hermes

Use this when a user wants proof that Claude slash commands work through a Hermes-driven interactive terminal, not just proof that Claude launched.

## Goal

Separate three different claims:

1. Claude launches visibly in the right repo.
2. The intended loadout/context file is actually applied.
3. Interactive input reaches Claude intact enough for slash commands and normal prompts to work.

Do not treat (1) or (2) as proof of (3).

## Minimal check sequence

1. Launch Claude visibly with the real user home forced and the repo-local loadout file appended.
2. Send one very short plain-text prompt first, such as:
   - `Say hello in one sentence.`
3. Capture the PTY/log output and compare the sent text to the received text shown in the TUI.
4. Only if the plain-text control prompt survives intact should you test a slash command such as:
   - `/goal reply with exactly 3 short bullet points proving slash commands work here`
5. Again compare intended input vs echoed/received input in the PTY/log before claiming slash-command success.

## Why this matters

In this session, visible Claude launch worked, the repo-local loadout append path worked, and `/goal` activation could be observed. But the Hermes interactive bridge dropped/collapsed characters during input delivery, so the agent could not honestly claim that slash commands were working end-to-end through the interface.

Examples from the captured PTY path:

- Intended: `Say hello in one sentence.`
- Received in TUI: `Sahello in one setnce.`

- Intended: `/goal reply with exactly 3 short bullet points proving slash commands work here`
- Received in TUI: `/goal reply with exactly 3 shortbulletpointsprovingslashcommandswork here`

## Reporting rule

If input integrity is not proven, report:

- visible Claude launch: verified
- applied loadout file: verified
- interactive slash-command delivery through Hermes: unverified due to input corruption in the PTY bridge

Do not overstate the result just because the window opened or because Claude showed an active-goal indicator.
