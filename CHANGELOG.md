# Changelog — 0.1.0 — 2026-08-04

All notable public-release changes for Hermes Valkyrie are tracked here. The current public launch milestone is **0.1.0**, released **2026-08-04**; this changelog is the version source of truth for the public repo.

Early development used small semantic pre-release versions (`0.001`, `0.002`, ...) to tell the story of how the system reached the first public launch readiness milestone, `0.1.0`.

## [0.1.0] — 2026-08-04 — First public launch readiness milestone

Initial public-preview release candidate (public name: Hermes Valkyrie). This milestone marks the repository as ready for its first public launch: the shareable surface is defined, sanitized, validated, and separated from private operator material.

### Added

- Sanitized public extraction workflow (maintainer development-workspace tooling) used to prepare shareable releases like this one.
- Public-safe GitHub Actions workflow that validates loadouts, route resolution, Claude/Codex sandbox materialization, command inventory comparison, clean onboarding smoke, and whitespace checks without non-public development files.
- Public onboarding docs for humans and agents, including Hermes install guidance and clean sandbox smoke testing.
- Root `README.md` established as the public GitHub front door, then refined with screenshot-inspired intro badges, dependency-only prerequisites with verified versions, a detailed Hermes clean-session install prompt, installation process, essential-system overview, loadout itinerary, and restored project tree.
- Separate docs-folder overview renamed to avoid two different files sharing the README name.
- Frozen Hermes gateway skill snapshots for the managed Claude Code/Codex control-plane surface.
- Public runtime scripts for loadout validation, route resolution, sandbox materialization, managed launching, and clean onboarding smoke tests.
- Maintainer-side release-readiness tooling for extraction safety, documentation checks, generated review bundles, and leak scanning (kept in the maintainer workspace; not part of the public artifact).

### Changed

- Simplified the source-checkout boundary to a strict partition: every tracked file outside the top-level private workspace folder is publicly shareable and either ships through the extraction workflow or sits on an explicit exclusion ledger; operator-only sync/audit scripts moved into the private workspace.
- Public artifact now ships the loadout apply wrappers, the live-system apply script, and the managed run-request contract module alongside the previously shipped runtime scripts.

### Removed

- Removed the standalone `VERSION` file so public release metadata is explicit in this changelog instead of split across two files.

### Security

- Development-only operator material is excluded from the public artifact.
- Public copy scans block private markers, absolute local paths, credentials-like content, and sanitizer prose regressions.

## [0.006] — 2026-08-04 — Unreferenced shared skills made private

### Changed

- Moved shared skills with no active loadout references out of the public surface and into the private tree, keeping the shared skill catalog limited to skills that materialized loadouts actually use.

## [0.005] — 2026-08-04 — Private maintenance surfaces relocated

### Changed

- Moved maintenance-only scripts, docs, and support surfaces out of the repository root, so the root reflects only the public product shape.

## [0.004] — 2026-08-04 — Devwork-only surfaces moved under private

### Changed

- Relocated development-only tests, docs, and working artifacts away from the public-facing repository layout.

## [0.003] — 2026-08-04 — Public shareability surface narrowed

### Changed

- Narrowed the set of files and docs considered publicly shareable, tightening the boundary that the extraction and leak-scan tooling enforces.

## [0.002] — 2026-08-04 — Managed launch hardening

### Fixed

- Made managed terminal launches bypass-deterministic, so the managed runner path resolves launch policy the same way every time.

### Docs

- Aligned the managed launch skill documentation with the bypass invariant so the documented contract matches runtime behavior.

## [0.001] — 2026-05-28 — Initial documentation and baseline

### Added

- Initial Hermes terminal loadout system scaffold: loadout definitions, shared instruction backbone, runtime adapters for Claude Code and Codex, and the routing system that materializes loadouts into managed terminal sessions.
- Baseline documentation set covering the loadout architecture, default loadout design, and system naming.
