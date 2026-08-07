# Minimalist Editorial UI

## Provenance

Adapted from `Leonxlnx/taste-skill` at revision `b17742737e796305d829b3ad39eda3add0d79060`, specifically `skills/minimalist-skill/SKILL.md`. This is a distilled Hermes loadout skill, not a vendored copy of the taste-skill plugin, its installer script, or its other aesthetic skills.

## When to use

Use this during frontend-design work when the target aesthetic is clean, editorial, "document-style" minimalism — refined workspace-tool and content surfaces built on a warm monochrome palette, strong typographic hierarchy, generous whitespace, and flat bento layouts.

Do not use it when the brief calls for a different aesthetic (bold, brutalist, glass, neon), for backend-only work, or as a general design-quality gate — for the broad quality bar use `impeccable-design-quality`. This skill is one aesthetic lens, not a replacement for it.

## Banned defaults

Reject the generic SaaS look. Do not ship:

- The `Inter`, `Roboto`, or `Open Sans` typefaces, or thin-line icon sets (`Lucide`, `Feather`, stock `Heroicons`).
- Tailwind's default heavy shadows (`shadow-md`/`lg`/`xl`); shadows must be near-invisible, ultra-diffuse, opacity below `0.05`.
- Large primary-colored backgrounds, gradients as decoration, neon, or 3D glassmorphism (subtle navbar blur excepted).
- `rounded-full` on large containers, cards, or primary buttons.
- Emojis in code, markup, content, or alt text; placeholder names (`John Doe`, `Acme Corp`, `Lorem Ipsum`); and AI copy clichés (`Elevate`, `Seamless`, `Unleash`, `Next-Gen`, `Game-changer`, `Delve`).

## Typography

- Body/UI: geometric or system sans with character (`SF Pro Display`, `Geist Sans`, `Helvetica Neue`, `Switzer`).
- Editorial headings/quotes: high-contrast serif (`Lyon Text`, `Newsreader`, `Playfair Display`, `Instrument Serif`) with tight tracking (`-0.02em` to `-0.04em`) and tight line-height (`~1.1`).
- Code/keystrokes/meta: monospace (`Geist Mono`, `SF Mono`, `JetBrains Mono`).
- Never pure black body text: use off-black/charcoal (`#111111`, `#2F3437`) at `line-height: 1.6`; secondary text muted gray (`#787774`).

## Warm monochrome palette

Color is scarce — semantic accents only.

- Canvas: pure white `#FFFFFF` or warm bone `#F7F6F3` / `#FBFBFA`.
- Card surface: `#FFFFFF` or `#F9F9F8`. Borders/dividers: `#EAEAEA` or `rgba(0,0,0,0.06)`.
- Accents: desaturated washed-out pastels only, e.g. pale red `#FDEBEC` (text `#9F2F2D`), pale blue `#E1F3FE` (text `#1F6C9F`), pale green `#EDF3EC` (text `#346538`), pale yellow `#FBF3DB` (text `#956400`).

## Components

- Bento grids: asymmetrical CSS grid, cards `border: 1px solid #EAEAEA`, crisp radius `8px`–`12px` max, generous `24px`–`40px` padding.
- Primary CTA: solid `#111111` on white text, radius `4px`–`6px`, no shadow, hover to `#333333` or `scale(0.98)`.
- Tags/badges: pill, `text-xs`, uppercase, wide tracking (`0.05em`), muted-pastel background.
- Accordions: no container boxes; separate with `border-bottom: 1px solid #EAEAEA` and a sharp `+`/`-` toggle.
- Keystrokes: `<kbd>` with `1px solid #EAEAEA`, radius `4px`, `#F7F6F3` background, monospace.
- Icons: `Phosphor` (Bold/Fill) or `Radix` at standardized stroke width.

## Motion

Motion is present but invisible — quiet, not spectacle.

- Scroll entry via `IntersectionObserver` (never a scroll listener): `translateY(12px)` + `opacity:0` resolving over `~600ms` with `cubic-bezier(0.16, 1, 0.3, 1)`.
- Hover: cards lift with a tiny shadow shift (`0 0 0` → `0 2px 8px rgba(0,0,0,0.04)`, `200ms`); buttons `scale(0.98)` on `:active`.
- Staggered list/grid reveals via `animation-delay: calc(var(--index) * 80ms)`.
- Animate only `transform` and `opacity`; never layout properties. Add reduced-motion alternatives.

## Execution and verification

- Establish macro-whitespace first (`py-24`+ between sections); constrain reading width to `max-w-4xl`/`max-w-5xl`.
- Give sections depth (low-opacity imagery, soft radial spots, subtle line patterns) — no empty flat backgrounds.
- Verify visually: run locally, screenshot desktop and a narrow width when layout changed, check hover/focus/disabled/empty states, and report what was actually verified and any gaps.
