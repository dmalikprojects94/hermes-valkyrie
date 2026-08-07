# Ponytail Audit

Whole-repo over-engineering audit. Like Ponytail Review, but scans a codebase instead of only a diff.

## When to invoke

- Operator says “audit for over-engineering”, “what can I delete from this repo”, “find bloat”, “ponytail-audit”, or asks for a simplification audit.
- Use as a one-shot report before cleanup work. Do not apply fixes unless separately asked.

## Hunt

Look for:

- dependencies that stdlib/native platform features replace
- interfaces with one implementation
- factories with one product
- wrappers that only delegate
- files exporting one tiny thing
- dead flags/config
- speculative extension points
- hand-rolled stdlib/platform behavior

## Output

Rank biggest cuts first:

`<tag>: <what to cut>. <replacement>. [path]`

Tags are `delete`, `stdlib`, `native`, `yagni`, and `shrink`.

End with: `net: -<N> lines, -<M> deps possible.`

If nothing should be cut: `Lean already. Ship.`

## Boundaries

Complexity-only. Correctness, security, and performance findings belong in normal review. Reads and reports only.

## Provenance

- Source: https://github.com/DietrichGebert/ponytail, rev `795ec0ee3678d2fd92f7d118396855e9dcd591dc`.
- Upstream file: `skills/ponytail-audit/SKILL.md`.
- Disposition: distilled-into-default.