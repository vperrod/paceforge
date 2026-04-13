---
name: design-engineering
description: "UI polish, animation decisions, component design, and the invisible details that make software feel great. Based on Emil Kowalski's design engineering philosophy."
---

# Design Engineering

## Core Philosophy

### Taste is trained, not innate

Good taste is not personal preference. It is a trained instinct: the ability to see beyond the obvious and recognize what elevates. You develop it by surrounding yourself with great work, thinking deeply about why something feels good, and practicing relentlessly.

### Unseen details compound

Most details users never consciously notice. That is the point. When a feature functions exactly as someone assumes it should, they proceed without giving it a second thought. That is the goal.

> "All those unseen details combine to produce something that's just stunning, like a thousand barely audible voices all singing in tune." - Paul Graham

### Beauty is leverage

People select tools based on the overall experience, not just functionality. Good defaults and good animations are real differentiators. Beauty is underutilized in software. Use it as leverage to stand out.

## Review Format (Required)

When reviewing UI code, use a markdown table with Before/After columns:

| Before | After | Why |
| --- | --- | --- |
| `transition: all 300ms` | `transition: transform 200ms ease-out` | Specify exact properties; avoid `all` |
| `transform: scale(0)` | `transform: scale(0.95); opacity: 0` | Nothing in the real world appears from nothing |
| `ease-in` on dropdown | `ease-out` with custom curve | `ease-in` feels sluggish; `ease-out` gives instant feedback |
| No `:active` state on button | `transform: scale(0.97)` on `:active` | Buttons must feel responsive to press |

## The Animation Decision Framework

### 1. Should this animate at all?

| Frequency | Decision |
| --- | --- |
| 100+ times/day (keyboard shortcuts, command palette toggle) | No animation. Ever. |
| Tens of times/day (hover effects, list navigation) | Remove or drastically reduce |
| Occasional (modals, drawers, toasts) | Standard animation |
| Rare/first-time (onboarding, feedback forms, celebrations) | Can add delight |

**Never animate keyboard-initiated actions.** These actions are repeated hundreds of times daily.

### 2. What is the purpose?

Valid purposes:
- **Spatial consistency**: toast enters and exits from the same direction
- **State indication**: a morphing feedback button shows the state change
- **Explanation**: a marketing animation that shows how a feature works
- **Feedback**: a button scales down on press, confirming the interface heard the user
- **Preventing jarring changes**: elements appearing or disappearing without transition feel broken

If the purpose is just "it looks cool" and the user will see it often, don't animate.

### 3. What easing should it use?

- Element entering → **ease-out** (starts fast, feels responsive)
- Moving/morphing on screen → **ease-in-out** (natural acceleration/deceleration)
- Hover/color change → **ease**
- Constant motion (marquee, progress bar) → **linear**
- Default → **ease-out**

**Use custom easing curves.** Built-in CSS easings are too weak:

```css
--ease-out: cubic-bezier(0.23, 1, 0.32, 1);
--ease-in-out: cubic-bezier(0.77, 0, 0.175, 1);
--ease-drawer: cubic-bezier(0.32, 0.72, 0, 1);
```

**Never use ease-in for UI animations.** It starts slow, making the interface feel sluggish.

### 4. How fast should it be?

| Element | Duration |
| --- | --- |
| Button press feedback | 100-160ms |
| Tooltips, small popovers | 125-200ms |
| Dropdowns, selects | 150-250ms |
| Modals, drawers | 200-500ms |
| Marketing/explanatory | Can be longer |

**Rule: UI animations should stay under 300ms.**

## Component Building Principles

### Buttons must feel responsive
Add `transform: scale(0.97)` on `:active`. Scale should be subtle (0.95-0.98).

### Never animate from scale(0)
Start from `scale(0.9)` or higher, combined with opacity. Even a barely-visible initial scale makes entrance feel natural.

### Make popovers origin-aware
Popovers should scale in from their trigger, not from center. **Exception: modals** keep `transform-origin: center`.

### Tooltips: skip delay on subsequent hovers
Once one tooltip is open, hovering over adjacent tooltips should open them instantly with no animation.

### Use CSS transitions over keyframes for interruptible UI
CSS transitions can be interrupted and retargeted mid-animation. Keyframes restart from zero.

### Use blur to mask imperfect transitions
When a crossfade feels off, add subtle `filter: blur(2px)` during the transition. Keep blur under 20px.

## Spring Animations

Springs feel more natural than duration-based animations because they simulate real physics.

**When to use springs:**
- Drag interactions with momentum
- Elements that should feel "alive"
- Gestures that can be interrupted mid-animation
- Decorative mouse-tracking interactions

**Spring configuration (Apple's approach):**
```js
{ type: "spring", duration: 0.5, bounce: 0.2 }
```

Keep bounce subtle (0.1-0.3). Springs maintain velocity when interrupted — CSS animations restart from zero.

## Gesture and Drag Interactions

### Momentum-based dismissal
Calculate velocity: `Math.abs(dragDistance) / elapsedTime`. If velocity exceeds ~0.11, dismiss regardless of distance.

### Damping at boundaries
When dragging past natural boundary, apply damping. Things in real life don't suddenly stop.

### Pointer capture for drag
Once dragging starts, capture all pointer events to continue even if pointer leaves bounds.

### Multi-touch protection
Ignore additional touch points after initial drag begins.

## Performance Rules

- **Only animate transform and opacity** — these skip layout and paint, running on GPU
- **CSS animations beat JS under load** — CSS runs off main thread
- **Use WAAPI for programmatic CSS animations** — hardware-accelerated, interruptible, no library needed
- **Framer Motion `x`/`y` props are NOT hardware-accelerated** — use full `transform` string instead

## Accessibility

### prefers-reduced-motion
Reduced motion means fewer and gentler animations, not zero. Keep opacity and color transitions. Remove movement and position animations.

### Touch device hover states
Gate hover animations behind `@media (hover: hover) and (pointer: fine)`.

## Stagger Animations

When multiple elements enter together, stagger their appearance with 30-80ms delays between items. Long delays make the interface feel slow.

## Review Checklist

| Issue | Fix |
| --- | --- |
| `transition: all` | Specify exact properties |
| `scale(0)` entry | Start from `scale(0.95)` with `opacity: 0` |
| `ease-in` on UI element | Switch to `ease-out` or custom curve |
| Animation on keyboard action | Remove animation entirely |
| Duration > 300ms on UI element | Reduce to 150-250ms |
| Hover without media query | Add `@media (hover: hover) and (pointer: fine)` |
| Keyframes on rapidly-triggered element | Use CSS transitions |
| Elements all appear at once | Add stagger delay (30-80ms) |
