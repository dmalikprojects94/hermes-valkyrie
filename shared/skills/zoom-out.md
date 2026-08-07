# Zoom Out

Higher-level orientation when the runtime is lost in details. Distilled from Matt Pocock's `zoom-out` skill.

## When to invoke

- Runtime is unsure how the code under inspection fits into the broader system.
- Operator says "zoom out", "give me the bigger picture", "what does this module connect to".
- A change is about to land in unfamiliar code.

## Output

A short map covering:
- The module's role in one sentence.
- The 2-5 modules that call into it (with one-line purpose each).
- The 2-5 modules it depends on.
- The seam(s) where behavior could be altered without editing in place.
- Any domain term the module embodies that callers use.

## Discipline

- Use the project's existing domain vocabulary. If a `CONTEXT.md` or glossary exists, prefer those names.
- Stop at one layer up. Two layers up is a different request.
- Do not propose changes. The zoom-out is orientation only.

## Provenance

- Source: https://github.com/mattpocock/skills, classified in internal maintainer ingestion notes (2026-05-28, not shipped publicly).
- Disposition: distilled-into-default.
- Notes: adapted into the Hermes default backbone as a small, runtime-portable shared skill.
