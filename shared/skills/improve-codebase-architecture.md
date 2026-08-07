# Improve Codebase Architecture

Surface architectural friction and propose deepening opportunities — refactors that turn shallow modules into deep ones. Distilled from Matt Pocock's `improve-codebase-architecture` skill.

## When to invoke

- Operator wants to improve testability, AI-navigability, or maintainability of a codebase.
- A bug post-mortem has surfaced a missing seam.
- The codebase has accumulated shallow modules and tangled callers.

## Vocabulary

Use these terms consistently across suggestions.

- **Module** — anything with an interface and an implementation (function, class, package, slice).
- **Interface** — everything a caller must know to use the module: types, invariants, error modes, ordering, config.
- **Depth** — leverage at the interface. Deep = high leverage. Shallow = interface nearly as complex as the implementation.
- **Seam** — where an interface lives; a place behavior can be altered without editing in place.
- **Locality** — change, bugs, and knowledge concentrated in one place.

Key heuristics:
- **Deletion test** — imagine deleting the module. If complexity vanishes, it was a pass-through. If complexity reappears across N callers, it was earning its keep.
- The interface is the test surface.
- One adapter = hypothetical seam. Two adapters = real seam.

## Process

### 1. Explore

If the project has a domain glossary or ADR directory, read those first. They name the good seams and record decisions the skill should not re-litigate.

Then walk the codebase looking for friction:
- Where does understanding one concept require bouncing between many small modules?
- Where are modules shallow — interface nearly as complex as the implementation?
- Where have pure functions been extracted just for testability, but the real bugs hide in how they are called?
- Where do tightly-coupled modules leak across their seams?
- Which parts are untested or hard to test through their current interface?

Apply the deletion test to anything you suspect is shallow.

### 2. Present candidates

For each candidate, produce:
- **Files** involved.
- **Problem** — why the current shape is causing friction.
- **Solution** — plain English description of what would change.
- **Benefits** — in terms of locality and leverage, and how tests would improve.
- **Before / after sketch** — minimal diagram or pseudocode pair.
- **Recommendation strength** — Strong, Worth exploring, or Speculative.

If any candidate contradicts an ADR, mark it as such and only surface it when the friction is real enough to warrant reopening the ADR.

End with a top recommendation: which candidate to tackle first and why.

### 3. Grilling loop

Once the operator picks a candidate, walk the design tree with them — constraints, dependencies, the shape of the deepened module, what sits behind the seam, what tests survive.

Side effects happen inline:
- Naming a new module after a concept not yet in the glossary -> add it.
- Sharpening a fuzzy term during the conversation -> update the glossary.
- Operator rejects the candidate with a load-bearing reason -> offer an ADR so the next architecture pass does not re-suggest it.

## Discipline

- Do not propose interfaces in the candidate presentation. Save interface design for the grilling loop, after a candidate is picked.
- Recommendations should be ranked, not bulk-listed.
- Architecture proposals are advisory. Do not auto-apply changes.
- A "good candidate" that contradicts the Hermes reporting contract or operating rules is not actually a good candidate.
