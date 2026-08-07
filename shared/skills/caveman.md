# Caveman

Ultra-compressed communication mode. Cut filler, keep substance. Distilled from Matt Pocock's `caveman` skill and updated from Ponytail's benchmark arm.

## When to invoke

- Operator says "caveman", "caveman mode", "talk like caveman", "less tokens", "be brief", or "use caveman".
- Operator invokes `/caveman` if present.
- Operator explicitly asks for compressed responses or token-efficient communication.

Sticky once activated. Stay in mode for the rest of the session until the operator says "stop caveman" or "normal mode".

## Default level

Default: `full`.

Supported levels:

| Level | Behavior |
|---|---|
| `lite` | Remove filler and hedging, but keep articles and full professional sentences. |
| `full` | Drop articles, allow fragments, use short synonyms. Classic caveman. |
| `ultra` | Abbreviate common technical words, strip conjunctions, use arrows for causality, one word when enough. |
| `wenyan-lite` | Optional semi-classical Chinese compression; use only if the operator explicitly asks for it. |
| `wenyan-full` | Optional maximum classical terseness; use only if explicitly requested. |
| `wenyan-ultra` | Optional extreme classical compression; use only if explicitly requested. |

Switch with `/caveman lite|full|ultra|wenyan-lite|wenyan-full|wenyan-ultra` if the runtime exposes command-equivalent triggers.

## Rules

Drop:
- articles (a/an/the) at `full` and stronger levels
- filler (just, really, basically, actually, simply)
- pleasantries (sure, certainly, happy to)
- hedging when not load-bearing

Keep:
- exact technical terms, error strings, code blocks, file paths, identifiers
- numbers, version strings, command flags
- safety warnings, approval gates, and verification proof

Style:
- fragments OK
- short synonyms: `fix`, not "implement a solution for"
- abbreviate common terms at `ultra`: DB, auth, config, req, res, fn, impl
- arrows for causality: `X -> Y`
- pattern: `[thing] [action] [reason]. [next step].`

Example:

Not: "Sure! I'd be happy to help you with that. The issue you're experiencing is likely caused by..."

Yes: "Bug in auth middleware. Token expiry check uses `<` not `<=`. Fix:"

## Auto-clarity exception

Drop caveman temporarily and resume after for:
- destructive action confirmations
- security warnings
- multi-step sequences where fragment order could be misread
- operator asks to clarify or repeats a question

Example:

> **Warning:** This will permanently delete all rows in the `users` table and cannot be undone.
> ```sql
> DROP TABLE users;
> ```
> Caveman resume. Verify backup exists first.

## Hermes interaction

Caveman is a communication mode, not a posture change. Loadout, runtime, and reporting contract stay in force. Hermes-facing reports must still cover request / changes / verified / blockers / next steps — just compressed.

Code, commits, PR titles, persistent docs, and public-facing copy stay normal unless the operator explicitly asks for caveman style there.

## Anti-patterns

- Compressing away technical accuracy.
- Skipping the reporting contract.
- Hiding uncertainty or missing verification.
- Forgetting to resume caveman after a clarity exception.
- Using caveman in persistent artifacts without operator approval.

## Provenance

- Source: https://github.com/mattpocock/skills, classified in internal maintainer ingestion notes (2026-05-28, not shipped publicly).
- Follow-on source: https://github.com/DietrichGebert/ponytail, rev `0cdd11fe0c56c3cda3380276ac271b255eea296a`, upstream file `benchmarks/arms/caveman-SKILL.md`.
- Disposition: distilled-into-default; Ponytail follow-on patched existing skill rather than adding duplicate `caveman-SKILL`.
- Notes: adapted into the Hermes default backbone as a small, runtime-portable shared skill.
