# Operator personalization

Every operator-specific value comes from a local `.env` file built from the
`.env.example` template at the repo root. `.env` is git-ignored and must never
be committed. This guide maps each variable onto what it configures.

## Getting started

```bash
cp .env.example .env
# edit .env and replace each <placeholder> with your own value
```

Leave a variable unset to take its documented default. Optional integrations
that are unset are simply skipped.

## Personalization classes

### Runtime home

Runtime homes are derived from your shell's `$HOME`; there is no baked-in path.
You normally leave `HOME` at your shell default. Only override it if you run the
agent under a home directory other than your login user's.

### Save destination routing

`SAVE_DESTINATION_PATH` — optional absolute path to any folder where durable run
captures should be saved. For an Obsidian setup, this can be the vault path. For
everyone else, it can be a normal notes, logs, or artifacts folder. Leave it
unset to fall back to `./local-runtime-artifacts/raw-capture/` from the current
working directory.

`OBSIDIAN_VAULT_PATH` is still honored as a legacy compatibility alias for
existing Hermes deployments, but new public setups should use
`SAVE_DESTINATION_PATH`.

### Reportback routing (Discord)

Optional. Used to post run closeouts to a Discord thread.

- `DISCORD_BOT_TOKEN` — the bot secret. Env-only, never committed. Create a bot
  in the Discord developer portal and paste its token into `.env`.
- `DISCORD_GUILD_ID` — your server (guild) ID.
- `DISCORD_CHANNEL_ID` — the target channel ID.
- `DISCORD_THREAD_ID` — the target thread ID.
- `DISCORD_THREAD_NAME` — a human label for the thread.

Obtain numeric IDs from your own server with developer mode enabled
(right-click → Copy ID). All IDs in the template are placeholders.

### Public target account

`PUBLIC_TARGET_ACCOUNT` — the GitHub account or org you would publish a future
extracted public copy under. This is a value you choose; there is no default.

## Rules

- Never paste real tokens, IDs, or absolute machine paths into tracked files,
  including tests and docs.
- If a required value is missing at runtime, the system asks rather than
  guessing — supply it in `.env`.
