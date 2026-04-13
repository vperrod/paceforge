---
name: taste-design
description: "High-agency frontend design skill with parameterized dials for design variance, motion intensity, and visual density. Fights AI bias with engineered rules for premium, non-generic output."
---

# High-Agency Frontend Skill

## 1. ACTIVE BASELINE CONFIGURATION
* DESIGN_VARIANCE: 8 (1=Perfect Symmetry, 10=Artsy Chaos)
* MOTION_INTENSITY: 6 (1=Static/No movement, 10=Cinematic/Magic Physics)
* VISUAL_DENSITY: 4 (1=Art Gallery/Airy, 10=Pilot Cockpit/Packed Data)

Adapt these values dynamically based on what the user explicitly requests. Use these as global variables to drive the logic in Sections 3 through 7.

## 2. DEFAULT ARCHITECTURE & CONVENTIONS

* **DEPENDENCY VERIFICATION [MANDATORY]:** Before importing ANY 3rd party library, check `package.json`. If missing, output the installation command first.
* **Framework & Interactivity:** React or Next.js. Default to Server Components (RSC).
  * **RSC SAFETY:** Global state works ONLY in Client Components.
  * **INTERACTIVITY ISOLATION:** Interactive UI components MUST be extracted as isolated leaf components with `'use client'`.
* **Styling Policy:** Use Tailwind CSS (v3/v4) for 90% of styling.
  * **TAILWIND VERSION LOCK:** Check `package.json` first. Do not use v4 syntax in v3 projects.
* **ANTI-EMOJI POLICY [CRITICAL]:** NEVER use emojis in code, markup, text content, or alt text. Use high-quality icons (Radix, Phosphor) or clean SVG primitives.
* **Responsiveness & Spacing:**
  * Contain page layouts using `max-w-[1400px] mx-auto` or `max-w-7xl`.
  * **Viewport Stability [CRITICAL]:** NEVER use `h-screen`. ALWAYS use `min-h-[100dvh]`.
  * **Grid over Flex-Math:** NEVER use complex flexbox percentage math. ALWAYS use CSS Grid.

## 3. DESIGN ENGINEERING DIRECTIVES (Bias Correction)

**Rule 1: Deterministic Typography**
* **Display/Headlines:** Default to `text-4xl md:text-6xl tracking-tighter leading-none`.
  * **ANTI-SLOP:** Discourage `Inter`. Force unique character using `Geist`, `Outfit`, `Cabinet Grotesk`, or `Satoshi`.
  * Serif fonts are BANNED for Dashboard/Software UIs.
* **Body/Paragraphs:** Default to `text-base text-gray-600 leading-relaxed max-w-[65ch]`.

**Rule 2: Color Calibration**
* Max 1 Accent Color. Saturation < 80%.
* **THE LILA BAN:** "AI Purple/Blue" aesthetic is BANNED. No purple button glows, no neon gradients. Use absolute neutral bases (Zinc/Slate) with singular accents (Emerald, Electric Blue, or Deep Rose).
* **COLOR CONSISTENCY:** Stick to one palette for the entire output.

**Rule 3: Layout Diversification**
* **ANTI-CENTER BIAS:** Centered Hero/H1 sections are BANNED when `LAYOUT_VARIANCE > 4`. Force "Split Screen", "Left Aligned content/Right Aligned asset", or "Asymmetric White-space".

**Rule 4: Materiality, Shadows, and "Anti-Card Overuse"**
* **DASHBOARD HARDENING:** For `VISUAL_DENSITY > 7`, generic card containers are BANNED. Use `border-t`, `divide-y`, or negative space.
* Use cards ONLY when elevation communicates hierarchy. Tint shadows to the background hue.

**Rule 5: Interactive UI States**
* **Mandatory Generation:** Implement full interaction cycles:
  * **Loading:** Skeletal loaders matching layout sizes.
  * **Empty States:** Beautifully composed empty states indicating how to populate data.
  * **Error States:** Clear, inline error reporting.
  * **Tactile Feedback:** On `:active`, use `-translate-y-[1px]` or `scale-[0.98]`.

**Rule 6: Data & Form Patterns**
* Forms: Label MUST sit above input. Error text below input. Use standard `gap-2` for input blocks.

## 4. CREATIVE PROACTIVITY (Anti-Slop Implementation)

* **"Liquid Glass" Refraction:** Beyond `backdrop-blur`. Add `border-white/10` and `shadow-[inset_0_1px_0_rgba(255,255,255,0.1)]`.
* **Magnetic Micro-physics (MOTION_INTENSITY > 5):** Use EXCLUSIVELY Framer Motion's `useMotionValue` and `useTransform`. NEVER use `useState` for continuous animations.
* **Perpetual Micro-Interactions:** When `MOTION_INTENSITY > 5`, embed continuous micro-animations (Pulse, Typewriter, Float, Shimmer) with Spring Physics (`type: "spring", stiffness: 100, damping: 20`).
* **Layout Transitions:** Utilize Framer Motion's `layout` and `layoutId` props.
* **Staggered Orchestration:** Use `staggerChildren` or CSS cascade (`animation-delay: calc(var(--index) * 100ms)`).

## 5. PERFORMANCE GUARDRAILS

* Apply grain/noise filters exclusively to fixed, `pointer-events-none` pseudo-elements.
* **Hardware Acceleration:** Never animate `top`, `left`, `width`, or `height`. Use `transform` and `opacity` exclusively.
* **Z-Index Restraint:** Use z-indexes strictly for systemic layer contexts (Sticky Navbars, Modals, Overlays).

## 6. TECHNICAL REFERENCE (Dial Definitions)

### DESIGN_VARIANCE (Level 1-10)
* **1-3 (Predictable):** Strict symmetrical grids, equal paddings.
* **4-7 (Offset):** Overlapping margins, varied aspect ratios, left-aligned headers.
* **8-10 (Asymmetric):** Masonry layouts, CSS Grid with fractional units, massive empty zones.
* **MOBILE OVERRIDE:** For levels 4-10, asymmetric layouts MUST fall back to single-column on `< 768px`.

### MOTION_INTENSITY (Level 1-10)
* **1-3 (Static):** No automatic animations. CSS `:hover` and `:active` only.
* **4-7 (Fluid CSS):** `transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1)`. Focus on `transform` and `opacity`.
* **8-10 (Advanced Choreography):** Scroll-triggered reveals, parallax. Use Framer Motion hooks. NEVER use `window.addEventListener('scroll')`.

### VISUAL_DENSITY (Level 1-10)
* **1-3 (Art Gallery):** Lots of white space. Huge section gaps. Clean and expensive.
* **4-7 (Daily App):** Normal spacing for standard web apps.
* **8-10 (Cockpit):** Tiny paddings. No card boxes; just 1px lines. Use Monospace for numbers.

## 7. AI TELLS (Forbidden Patterns)

### Visual & CSS
* **NO Neon/Outer Glows.** Use inner borders or subtle tinted shadows.
* **NO Pure Black.** Use Off-Black, Zinc-950, or Charcoal.
* **NO Oversaturated Accents.** Desaturate accents to blend with neutrals.
* **NO Custom Mouse Cursors.** Ruins performance/accessibility.

### Typography
* **NO Inter Font.** Use `Geist`, `Outfit`, `Cabinet Grotesk`, or `Satoshi`.
* **NO Oversized H1s.** Control hierarchy with weight and color, not massive scale.
* Serif fonts ONLY for creative/editorial. NEVER on Dashboards.

### Layout & Spacing
* **NO 3-Column Card Layouts.** Use 2-column Zig-Zag, asymmetric grid, or horizontal scroll.
* Align & space perfectly. Avoid floating elements with awkward gaps.

### Content & Data
* **NO Generic Names** ("John Doe", "Jane Smith"). Use creative, realistic names.
* **NO Fake Numbers** (`99.99%`, `50%`). Use organic data (`47.2%`, `+1 (312) 847-1928`).
* **NO Startup Slop Names** ("Acme", "Nexus", "SmartFlow"). Invent premium brand names.
* **NO Filler Words** ("Elevate", "Seamless", "Unleash", "Next-Gen"). Use concrete verbs.

### External Resources
* **NO Unsplash.** Use `https://picsum.photos/seed/{random_string}/800/600` or SVG avatars.
* **shadcn/ui:** MUST customize radii, colors, shadows to match project aesthetic. Never use defaults.

## 8. THE CREATIVE ARSENAL (High-End Inspiration)

### Navigation & Menus
* Mac OS Dock Magnification, Magnetic Button, Dynamic Island, Contextual Radial Menu, Mega Menu Reveal

### Layout & Grids
* Bento Grid, Masonry Layout, Split Screen Scroll, Curtain Reveal

### Cards & Containers
* Parallax Tilt Card, Spotlight Border Card, Glassmorphism Panel, Holographic Foil Card, Morphing Modal

### Scroll-Animations
* Sticky Scroll Stack, Horizontal Scroll Hijack, Zoom Parallax, Scroll Progress Path

### Micro-Interactions
* Particle Explosion Button, Skeleton Shimmer, Directional Hover Aware Button, Ripple Click Effect, Mesh Gradient Background

## 9. FINAL PRE-FLIGHT CHECK

- [ ] Is mobile layout collapse (`w-full`, `px-4`, `max-w-7xl mx-auto`) guaranteed?
- [ ] Do full-height sections use `min-h-[100dvh]` instead of `h-screen`?
- [ ] Do `useEffect` animations contain strict cleanup functions?
- [ ] Are empty, loading, and error states provided?
- [ ] Are cards omitted in favor of spacing where possible?
- [ ] Did you isolate CPU-heavy perpetual animations in their own Client Components?
