---
name: impeccable-design
description: "Comprehensive design skill for distinctive, production-grade frontend interfaces. Covers typography, color, spatial design, motion, interaction, responsive design, and UX writing. Fights AI design monoculture with deep expertise."
---

This skill guides creation of distinctive, production-grade frontend interfaces that avoid generic "AI slop" aesthetics. Implement real working code with exceptional attention to aesthetic details and creative choices.

## Context Gathering Protocol

Design skills produce generic output without project context. You MUST have confirmed design context before doing any design work.

**Required context:**
- **Target audience**: Who uses this product and in what context?
- **Use cases**: What jobs are they trying to get done?
- **Brand personality/tone**: How should the interface feel?

## Design Direction

Commit to a BOLD aesthetic direction:
- **Purpose**: What problem does this interface solve? Who uses it?
- **Tone**: Pick an extreme: brutally minimal, maximalist chaos, retro-futuristic, organic/natural, luxury/refined, playful/toy-like, editorial/magazine, brutalist/raw, art deco/geometric, soft/pastel, industrial/utilitarian, etc.
- **Constraints**: Technical requirements (framework, performance, accessibility).
- **Differentiation**: What makes this UNFORGETTABLE?

## Frontend Aesthetics Guidelines

### Typography

<font_selection_procedure>
DO THIS BEFORE TYPING ANY FONT NAME.

Step 1. Write down 3 concrete words for the brand voice (e.g., "warm and mechanical and opinionated"). NOT "modern" or "elegant" — those are dead categories.

Step 2. List the 3 fonts you would normally reach for. They are likely from this banned list:

Fraunces, Newsreader, Lora, Crimson, Crimson Pro, Crimson Text, Playfair Display, Cormorant, Syne, IBM Plex Mono, IBM Plex Sans, IBM Plex Serif, Space Mono, Space Grotesk, Inter, DM Sans, DM Serif Display, DM Serif Text, Outfit, Plus Jakarta Sans, Instrument Sans, Instrument Serif

Reject every font in this list. They create monoculture across projects.

Step 3. Browse a font catalog with the 3 brand words in mind. Sources: Google Fonts, Pangram Pangram, Future Fonts, Adobe Fonts, Klim Type Foundry, Velvetyne.

Step 4. Cross-check: if your final pick lines up with your reflex pattern, go back to Step 3.
</font_selection_procedure>

Typography rules:
- DO use a modular type scale with fluid sizing (clamp) for headings on marketing pages. Use fixed `rem` scales for app UIs.
- DO vary font weights and sizes to create clear visual hierarchy.
- DO NOT use overused fonts (Inter, Roboto, Arial, Open Sans, system defaults).
- DO NOT use only one font family for the entire page. Pair a distinctive display font with a refined body font.
- DO NOT set long body passages in uppercase.
- Cap line length at ~65-75ch.

### Color & Theme

- Use OKLCH, not HSL. OKLCH is perceptually uniform.
- Tint your neutrals toward your brand hue. Even chroma of 0.005-0.01 creates subconscious cohesion.
- The 60-30-10 rule: 60% neutral/surface, 30% secondary text and borders, 10% accent.
- Theme should be DERIVED from audience and viewing context, not picked from a default.

Color rules:
- DO NOT use gray text on colored backgrounds; use a shade of the background color instead.
- DO NOT use pure black (#000) or pure white (#fff). Always tint.
- DO NOT use the AI color palette: cyan-on-dark, purple-to-blue gradients, neon accents on dark backgrounds.
- DO NOT use gradient text. Solid colors only for text.
- DO NOT default to dark mode with glowing accents OR light mode "to be safe." Choose intentionally.

### Layout & Space

- Use a 4pt spacing scale with semantic token names (`--space-sm`, `--space-md`). Scale: 4, 8, 12, 16, 24, 32, 48, 64, 96.
- Use `gap` instead of margins for sibling spacing.
- Self-adjusting grid: `grid-template-columns: repeat(auto-fit, minmax(280px, 1fr))`.
- Container queries for components, viewport queries for page layout.

Layout rules:
- DO NOT wrap everything in cards. Not everything needs a container.
- DO NOT nest cards inside cards.
- DO NOT use identical card grids (same-sized cards with icon + heading + text, repeated endlessly).
- DO NOT center everything. Left-aligned text with asymmetric layouts feels more designed.
- DO NOT use the same spacing everywhere.

### Visual Details

**Absolute Bans — Most Recognizable AI Design Tells:**

BAN 1: Side-stripe borders on cards/list items/callouts/alerts
- PATTERN: `border-left:` or `border-right:` with width greater than 1px
- REWRITE: use full borders, background tints, leading numbers/icons, or no visual indicator.

BAN 2: Gradient text
- PATTERN: `background-clip: text` combined with a gradient background
- REWRITE: use a single solid color for text. Emphasis via weight or size.

Additional rules:
- DO NOT use glassmorphism everywhere.
- DO NOT use sparklines as decoration.
- DO NOT use rounded rectangles with generic drop shadows.
- DO NOT use modals unless there's truly no better alternative.

### Motion

- Use exponential easing (ease-out-quart/quint/expo) for natural deceleration.
- For height animations, use grid-template-rows transitions instead of animating height directly.
- DON'T animate layout properties (width, height, padding, margin). Use transform and opacity only.
- DON'T use bounce or elastic easing. They feel dated; real objects decelerate smoothly.

### Interaction

- Use progressive disclosure. Start simple, reveal sophistication through interaction.
- Design empty states that teach the interface, not just say "nothing here."
- Make every interactive surface feel intentional and responsive.
- DON'T make every button primary. Use ghost buttons, text links, secondary styles.

### Responsive

- Use container queries (@container) for component-level responsiveness.
- Adapt the interface for different contexts, not just shrink it.
- DON'T hide critical functionality on mobile. Adapt, don't amputate.

### UX Writing

- Make every word earn its place.
- DON'T repeat information users can already see.

## The AI Slop Test

**Critical quality check**: If you showed this interface to someone and said "AI made this," would they believe you immediately? If yes, that's the problem.

A distinctive interface should make someone ask "how was this made?" not "which AI made this?"

## Implementation Principles

Match implementation complexity to the aesthetic vision. Maximalist designs need elaborate code. Minimalist designs need restraint and precision.

Interpret creatively and make unexpected choices. No design should be the same. Vary between light and dark themes, different fonts, different aesthetics. NEVER converge on common choices across generations.
