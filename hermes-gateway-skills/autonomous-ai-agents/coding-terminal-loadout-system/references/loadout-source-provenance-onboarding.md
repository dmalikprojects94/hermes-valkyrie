# Loadout Source Provenance and Onboarding

Use this when the operator provides a promising GitHub repo, Claude Code pack, Codex pack, prompt pack, skill pack, hook pack, or runtime config bundle to integrate into the coding-terminal loadout system.

## Durable repo process

The loadout repo should treat upstream material as curated source material, not as a blind copy. A source pass is incomplete if it only says "not default" or "not a new loadout"; it must say what useful upstream behavior should be added, patched, deferred, or rejected for each existing loadout. For each source pass:

1. Inspect the upstream GitHub repo and record URL, clone/inspection path, revision/date, license, and source type.
2. Inventory the meaningful upstream files/capabilities before deciding what to adopt.
3. Classify every meaningful item with a disposition: `recommend-add`, `recommend-patch-existing`, `distilled-into-default`, `distilled-into-loadout`, `runtime-specific-adapter`, `repo-resident`, `superseded`, `deferred`, or `rejected`.
4. Produce a recommendation ledger grouped by target: `default`, `coding`, `deep-coding`, `project-planner`, `loadout-management`/adapters, and `rejected/deferred`. This ledger is required even when runtime materialization is still `0`.
5. Distill shared intent into `shared/instructions`, `shared/skills`, or `shared/packs` first.
6. Map that shared intent into Claude Code and Codex runtime surfaces as evenly as practical.
7. Record any intentional runtime gaps instead of claiming sync by name alone.
8. Update the maintainer source matrix plus a per-source ingestion report.
9. Add a short `## Provenance` section to any new or materially rebuilt frame file derived from upstream work.
10. Verify with `python scripts/validate_loadouts.py`, relevant runtime command inventory checks, and tests when code changed.

## Skill-pack recommendation rule

When the upstream repo contains real skill files such as `skills/*/SKILL.md`, `skills/**/*.md`, `.claude/commands/*.md`, `.claude/agents/*.md`, hook definitions, or Codex/Claude plugin skill surfaces, inspect those files directly. Do not rely only on the repo README, topics, or a candidate-loadout name.

The expected output is a source-path-level recommendation, not a vague bundle. For example, a skill repo like `obra/superpowers` should produce rows like:

- `skills/subagent-driven-development/SKILL.md` → recommend-add or recommend-patch-existing → `deep-coding`
- `skills/dispatching-parallel-agents/SKILL.md` → recommend-add or recommend-patch-existing → `deep-coding`
- `skills/using-git-worktrees/SKILL.md` → recommend-add or recommend-patch-existing → `deep-coding`
- `skills/verification-before-completion/SKILL.md` → superseded or patch-existing → existing `verification-loop`
- SessionStart/tool-map/bootstrap material → adapter-only → `loadout-management` / runtime adapters

If a source is not default-worthy and does not justify a new loadout, do not stop there. Route each useful skill into an existing loadout or existing shared surface, and state whether it is recommended for later application or already applied.

Use repo-pinned candidate identity in all ledgers: `<owner/repo>::<candidate-or-skill>`. Candidate names alone are not unique enough across GitHub skill repos.

## Canonical docs added in the loadout repo

The session that established this process added these maintainer docs (development checkout only, not shipped publicly):

- a source-provenance contract — upstream source citation, frame-file provenance, and disposition vocabulary.
- a reusable per-GitHub-repo ingestion report template.
- a loadout-synchronization contract — Claude/Codex parity categories and sync checklist.

The repo README, the maintainer source matrix, and the loadout-builder skill were also updated to point future work at this process.

## Generic GitHub source-list intake

Treat GitHub star lists as configurable intake queues, not one-off hard-coded tools. the operator's Claude Stack list is a saved list, but the executable helper should work with any GitHub star-list URL.

Canonical loadout-repo pattern:

- the maintainer source registry — registry of saved list aliases (maintainer development checkout only; not shipped in the public copy). A saved list lives here as an alias with a star-list URL of the form `https://github.com/stars/<github-user>/lists/<list-slug>`, a `queue_doc`, and a `priority_candidate`.
- the maintainer source-registry helper tool (not shipped publicly) — generic helper. It should support showing saved aliases, parsing a saved or arbitrary GitHub star list, and producing the first source-accounting plan for a repo. The tool may read the registry, but must not embed any one list URL as its only supported list.
- `shared/skills/source-list-onboarding.md` — repo-resident onboarding skill/tool explaining how to turn any saved alias or ad-hoc star-list URL into a source-accounted loadout decision.
- an optional per-list queue/index doc for a saved alias, with candidate repos and initial likely destinations.
- the maintainer source matrix and repo README — should mention the generic registry/tool so future agents do not treat star lists as informal browser bookmarks.

When the operator says "don't hard-code our list," preserve the list access as registry data and make the helper list-agnostic. Keep an offline test path using local star-list HTML so arbitrary-list parsing can be verified without depending on live GitHub page shape or network state.

Do not bulk-copy a queued upstream repo into `default`. For example, `ruvnet/ruflo` is a strong priority candidate because it advertises Claude Code + Codex surfaces, agents, skills, MCP, hooks/daemon concepts, and multi-agent workflow ideas, but it should be treated as a full source pass. Likely destinations are `deep-coding`, `project-planner`, research/memory ideas, or runtime adapters. `default` should receive only tiny distilled behavior that passes the default admission rule.

## Claude/Codex sync rule

Do not call a loadout synchronized just because both runtimes support the same loadout name. Synchronization means the user-facing behavior has an equivalent surface in both runtimes or a documented intentional gap.

Use parity categories like `synced`, `shared-only`, `claude-only-acceptable`, `codex-only-acceptable`, `missing-claude`, `missing-codex`, and `intentional-gap` in source reports and rebuild notes.

## Operator reporting

When finishing this class of work for the operator, report the files changed, validation output, and commit status. Do not commit the loadout repo unless the operator explicitly approves that commit.