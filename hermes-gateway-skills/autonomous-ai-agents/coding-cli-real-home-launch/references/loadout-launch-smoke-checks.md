# Integrated Hermes loadout launch smoke checks

Use this when validating the live `hermes loadout launch` path instead of calling `claude` or `codex` manually.

## Goal

Verify that the integrated launcher:

- applies the expected loadout
- launches the runtime in the intended repo
- preserves the real auth context with `HOME=/home/<operator>`
- gives Codex the expected `CODEX_HOME` value for the managed runtime home

## CLI quirks worth remembering

- `hermes loadout launch` requires either `--loadout <name>` or `--request <text>`.
- For forwarded runtime args, prefer `--arg=<value>` form, especially when the forwarded value itself starts with a dash such as `-p` or `--max-turns`.
- A reliable pattern is to repeat `--arg=...` once per forwarded token.

## Claude smoke sequence

Basic launcher proof:

```bash
export HOME=/home/<operator>
hermes loadout launch claude \
  --loadout deep-coding \
  --cwd /home/<operator>/projects/<GITHUB_REPO_NAME> \
  --arg=-p \
  --arg='Reply with exactly: CLAUDE_LOADOUT_SMOKE_OK' \
  --arg=--max-turns \
  --arg=1
```

Environment proof:

```bash
export HOME=/home/<operator>
hermes loadout launch claude \
  --loadout deep-coding \
  --cwd /home/<operator>/projects/<GITHUB_REPO_NAME> \
  --arg=--dangerously-skip-permissions \
  --arg=-p \
  --arg='Run shell commands to read the environment and working directory. Then reply with exactly two lines in this format: HOME=<value> and PWD=<value>.' \
  --arg=--max-turns \
  --arg=2
```

Expected output includes:

- `HOME=/home/<operator>`
- `PWD=/home/<operator>/projects/<GITHUB_REPO_NAME>`

Auth confirmation outside the launch wrapper:

```bash
HOME=/home/<operator> claude auth status --text
```

Expected output should show the logged-in Claude account details.

## Codex smoke sequence

Basic launcher proof:

```bash
export HOME=/home/<operator>
hermes loadout launch codex \
  --loadout research \
  --cwd /home/<operator>/projects/<GITHUB_REPO_NAME> \
  --arg=exec \
  --arg='Reply with exactly: CODEX_LOADOUT_SMOKE_OK'
```

Environment proof:

```bash
export HOME=/home/<operator>
hermes loadout launch codex \
  --loadout research \
  --cwd /home/<operator>/projects/<GITHUB_REPO_NAME> \
  --arg=exec \
  --arg='Run commands to inspect the environment and working directory, then reply with exactly three lines: HOME=<value>, CODEX_HOME=<value>, and PWD=<value>.'
```

Expected output includes:

- `HOME=/home/<operator>`
- `CODEX_HOME=/home/<operator>/.codex`
- `PWD=/home/<operator>/projects/<GITHUB_REPO_NAME>`

## Tiny real-task verification

After the environment smoke passes, ask each runtime for one tiny repo-aware task, for example:

- identify the top 3 files to touch for a small change to loadout apply behavior

Pass condition:

- the runtime answers from the repo context rather than failing auth or landing in the wrong home
- the file choices are plausible for the target repo

## Interpretation

If both launcher smoke tests and the tiny repo task succeed, the integrated Hermes loadout path is working well enough for user-level validation and merge/review.
