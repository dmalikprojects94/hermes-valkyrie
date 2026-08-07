# Ponytail Review

Review code only for unnecessary complexity. The best finding is a shorter diff.

## When to invoke

- Operator says “review for over-engineering”, “what can we delete”, “is this over-engineered”, “simplify review”, or “ponytail-review”.
- Use during review/cleanup phases after a normal correctness/security review, not as a replacement for them.

## Output format

One line per finding:

`<file>:L<line>: <tag>: <what to cut>. <replacement>.`

Tags:

- `delete:` dead code, unused flexibility, speculative feature. Replacement: nothing.
- `stdlib:` hand-rolled code the standard library already ships. Name the function/module.
- `native:` dependency or code doing what the platform already does. Name the feature.
- `yagni:` abstraction with one implementation, config nobody sets, layer with one caller.
- `shrink:` same logic in fewer lines. Show the shorter form.

End with: `net: -<N> lines possible.`

If nothing should be cut: `Lean already. Ship.`

## Boundaries

This is complexity-only review. Correctness, security, and performance issues belong in the normal review path. Do not flag the smallest runnable smoke test/self-check for removal; Ponytail requires a minimal check for non-trivial logic.

## Provenance

- Source: https://github.com/DietrichGebert/ponytail, rev `795ec0ee3678d2fd92f7d118396855e9dcd591dc`.
- Upstream file: `skills/ponytail-review/SKILL.md`.
- Disposition: distilled-into-default.