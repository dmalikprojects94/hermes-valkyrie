# Ponytail Debt

Collect deliberate `ponytail:` shortcuts into a debt ledger so simplifications stay intentional instead of rotting into invisible “later”.

## When to invoke

- Operator says “ponytail debt”, “what did Ponytail defer”, “list the shortcuts”, “ponytail ledger”, or “what did we mark to do later”.
- Use after Ponytail-heavy implementation passes or before cleanup planning.

## Scan

Search the repo for comment markers that include `ponytail:`. Skip `.git`, dependency directories, build output, generated caches, and vendored artifacts.

Each marker should name the simplification ceiling and the upgrade trigger/path.

## Output

Group by file:

`<file>:<line> — <what was simplified>. ceiling: <limit>. upgrade: <trigger/path>.`

Flag any marker with no upgrade trigger as `no-trigger`.

End with: `<N> markers, <M> with no trigger.`

If none found: `No ponytail: debt. Clean ledger.`

## Boundaries

Reads and reports only. Persist a ledger file only if explicitly asked.

## Provenance

- Source: https://github.com/DietrichGebert/ponytail, rev `795ec0ee3678d2fd92f7d118396855e9dcd591dc`.
- Upstream file: `skills/ponytail-debt/SKILL.md`.
- Disposition: distilled-into-default.