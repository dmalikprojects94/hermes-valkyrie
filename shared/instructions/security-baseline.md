# Security Baseline

Mandatory checks before any commit, regardless of loadout.

## Pre-commit security checks

- **No secrets in diffs.** Scan for API keys, tokens, passwords, private keys, OAuth client secrets, connection strings, `.env` payloads. Reject the commit if any appear, even in tests.
- **No credentials in URLs.** Never inline `user:pass@host` style auth.
- **No hardcoded prod paths.** No baked-in hostnames, S3 buckets, or DB connection strings that should be env-driven.
- **No newly exposed surfaces.** New endpoints, new file upload paths, new shell-exec call sites get an explicit security note in the diff.

## Input handling

- Treat all external input as untrusted until validated at the boundary.
- Parameterize SQL; never string-concat queries.
- Escape shell args; prefer argument arrays over `shell=True`.
- Validate and bound user-supplied paths before any filesystem access (no `../` traversal).
- HTML/JSX: render data, never eval it. No `dangerouslySetInnerHTML` without an explicit sanitizer.

## Auth and authz

- Never log full tokens, session IDs, or PII.
- Authentication checks happen at the boundary; authorization checks happen at the resource.
- Default-deny: a new route is unauthenticated until proven otherwise.

## Dependencies

- New dependencies get a license + maintenance sanity check before they land.
- No transitive surface expansion without a stated reason.
- Pin versions for security-sensitive libraries (crypto, auth, parsing).

## Destructive operations

- Operations that delete data, drop tables, force-push, or rewrite history require an explicit operator confirmation, not just code review.
- Add a dry-run path for any destructive command added to the codebase.

## When in doubt

Flag the concern in the diff, route to `security-reviewer`, do not silently ship.

## Provenance

- Source: local Claude-OC-System default backbone doctrine plus internal Hermes-operator adaptation.
- Disposition: distilled-into-default.
- Notes: migrated as lean shared instruction text so Claude Code and Codex can inherit the same default intent.
