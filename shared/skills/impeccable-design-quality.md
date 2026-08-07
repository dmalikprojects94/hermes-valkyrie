# Impeccable Design Quality

## Provenance

Adapted from `pbakaus/impeccable` at revision `0d1c34e9d0fcfff1070c7210cd808eda504105d7`, especially `skill/SKILL.src.md`, `README.md`, and `skill/reference/hooks.md`. This is a distilled Hermes loadout skill, not a vendored copy of Impeccable's CLI, hook runtime, browser extension, or provider packaging.

## When to use

Use this during frontend-design work: UI implementation, redesigns, landing pages, dashboards, product surfaces, component styling, visual QA, responsive polish, accessibility checks, UX copy refinement, motion, theme work, and final shipping polish.

Do not use it for backend-only work or for installing Impeccable's project-local hook/plugin system. Runtime hooks, detector scripts, browser extensions, provider manifests, and `npx impeccable` installation stay deferred unless the operator explicitly approves an adapter/runtime integration pass.

## Operating procedure

1. Ground the design in the project before changing UI.
   - Read existing product/design context if present: `PRODUCT.md`, `DESIGN.md`, README, route docs, or nearby feature docs.
   - Inspect at least one representative UI file: CSS/tokens/theme, component, page, or layout.
   - Preserve committed brand colors, design tokens, components, and interaction conventions when they work.

2. Classify the surface.
   - **Brand surface:** marketing site, landing page, campaign, portfolio, editorial page, or design-is-the-product work.
   - **Product surface:** app UI, admin tool, dashboard, form, settings, onboarding, data workflow, or design-serves-the-product work.
   - If the project is new and no design context exists, define the audience, job-to-be-done, tone, anti-references, platform, and success criteria before picking colors or layouts.

3. Choose the design action intentionally.
   - **Craft/shape:** plan and build a new feature or surface.
   - **Critique/audit:** review hierarchy, clarity, accessibility, responsiveness, performance, and emotional fit.
   - **Polish/harden:** production pass for design-system alignment, error states, edge cases, i18n, reduced motion, and mobile/tablet behavior.
   - **Bolder/quieter/distill:** adjust intensity without breaking product clarity.
   - **Animate/colorize/typeset/layout/delight:** focused enhancement passes.
   - **Clarify/adapt/optimize:** targeted fixes for copy, device behavior, or UI performance.

4. Apply the quality bar while coding.
   - Ship production-grade code, not a prototype, unless the task explicitly asks for a prototype.
   - Keep body text readable: contrast >= 4.5:1; large text >= 3:1.
   - Use body line lengths around 65-75ch for prose.
   - Use balanced heading wraps and pretty prose wraps where supported.
   - Use responsive grids like `repeat(auto-fit, minmax(280px, 1fr))` when the layout is truly grid-shaped.
   - Use flexbox for one-dimensional flows and grid for two-dimensional relationships.
   - Build a semantic z-index scale instead of arbitrary 999/9999 values.
   - Add reduced-motion alternatives for every meaningful animation.
   - Prefer motion that communicates hierarchy/state; avoid decorative reflex motion.

5. Reject common AI-design tells before committing.
   - No gradient text as decoration.
   - No side-stripe accent borders on cards/list items/callouts.
   - No glassmorphism by default.
   - No hero-metric template as a reflex.
   - No endless identical icon-card grids.
   - No tiny uppercase tracked eyebrow above every section.
   - No numbered section markers unless the content is actually ordered.
   - No text overflow at tablet/mobile widths.
   - Do not default to cream/sand/beige warm-neutral backgrounds just because the brand feels warm.
   - Do not animate images on hover just because the parent card is hovered.
   - Do not pair 1px borders with large soft shadows as generic ghost-card decoration.
   - Do not over-round cards/sections/inputs beyond the brand's actual radius system.
   - Do not use sketchy/doodle SVGs as a fallback when real assets are unavailable.
   - Do not add decorative stripe/grid backgrounds unless the surface is actually a canvas/map/blueprint/measurement tool.

6. Verify visually.
   - Run the project locally when possible.
   - Use browser/screenshot verification for meaningful UI changes.
   - Check at least desktop and a narrow mobile/tablet width when layout changed.
   - Verify interactive states: hover/focus/disabled/loading/error/empty states where relevant.
   - Report what was actually verified and any gaps.

## Hooks and detector boundary

Impeccable upstream includes a deterministic detector and project-local hooks. In this loadout, treat that as deferred adapter material. You may recommend a future adapter pass, but do not install, enable, or assume Impeccable hooks during normal frontend-design runs.

If a future task explicitly asks for hook integration, scope it as a separate adapter project: Claude/Codex parity, project-local opt-in, safe failure behavior, source-accounting, and a reversible hook canary are required before live use.
