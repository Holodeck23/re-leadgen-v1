# DESIGN.md — Real Estate Lead Gen Landing Page

Design system for `site/index.html` and `site/thank-you.html`. Claude reads this before generating or modifying any page markup or styles.

## Design philosophy

Trust-first. Real estate buyers are spending $50K–$500K+ sight unseen from an ad. Every pixel must say "legitimate operation" not "flashy landing page." Photography does the selling — the UI stays out of the way.

Inspired by: Airbnb (warm, photography-forward, trust-building), Stripe (clean typography, generous white space), Cal.com (neutral palette, clear hierarchy).

## Color tokens

```css
:root {
  /* Surface */
  --bg:          #fafaf7;      /* warm off-white — not clinical, not yellow */
  --card:        #ffffff;
  --card-hover:  #f7f5f0;
  --line:        #e6e1d4;      /* warm rule lines */

  /* Text */
  --fg:          #1a1a1a;      /* near-black, not pure #000 */
  --muted:       #666660;      /* secondary text */
  --subtle:      #99958d;      /* tertiary, captions */

  /* Accent — earthy gold, not flashy */
  --accent:      #8a6d2a;      /* primary CTA, links */
  --accent-hover:#7a5f22;
  --accent-light:#f5f0e4;      /* accent background tint */

  /* Status */
  --success:     #2d7a4f;
  --error:       #b00020;
  --whatsapp:    #25d366;

  /* Overlay */
  --hero-overlay: linear-gradient(
    180deg,
    rgba(0,0,0,0.20) 0%,
    rgba(0,0,0,0.55) 100%
  );
}
```

**Dark mode:** Not needed. RE landing pages from ads are single-session, not daily-use tools.

**Per-property customization:** The accent color can be overridden in `property.json` → `branding.accent_color` if the property has brand colors. Default gold works for 90% of developments.

## Typography

```css
/* System stack — fast load, no FOUT, professional */
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
             "Helvetica Neue", Arial, sans-serif;

/* Scale — modular, clamp-based for fluid sizing */
--text-xs:   12px;
--text-sm:   14px;
--text-base: 16px;     /* body */
--text-lg:   18px;
--text-xl:   clamp(20px, 2.5vw, 24px);
--text-2xl:  clamp(24px, 3.5vw, 32px);
--text-3xl:  clamp(28px, 5vw, 42px);
--text-hero: clamp(32px, 6vw, 52px);

/* Weights */
--font-normal:   400;
--font-medium:   500;
--font-semibold: 600;
--font-bold:     700;

/* Line heights */
--leading-tight:  1.15;  /* hero headlines */
--leading-snug:   1.3;   /* section headlines */
--leading-normal: 1.55;  /* body text */
--leading-loose:  1.7;   /* long-form if needed */
```

**Rules:**
- Hero H1: `--text-hero`, `--font-bold`, `--leading-tight`. Max 20 characters per line on mobile.
- Section H2: `--text-2xl`, `--font-semibold`, `--leading-snug`.
- Body: `--text-base`, `--font-normal`, `--leading-normal`.
- Captions/labels: `--text-sm`, `--font-semibold`, uppercase tracking only for badges.
- Never use more than 2 font weights on a single page. Bold for headlines, normal for body.

## Spacing

```css
--space-xs:  4px;
--space-sm:  8px;
--space-md:  16px;
--space-lg:  24px;
--space-xl:  32px;
--space-2xl: 48px;
--space-3xl: 64px;
--space-4xl: 96px;

/* Page container */
--max-width: 1040px;
--page-pad:  24px;  /* horizontal padding */
```

**Section rhythm:** Each `<section>` gets `padding: var(--space-2xl) 0` and a `border-bottom: 1px solid var(--line)`. Consistent vertical rhythm is more important than any individual spacing decision.

## Components

### Hero

```
┌──────────────────────────────────────────────┐
│  [fullscreen video/photo with overlay]        │
│                                               │
│  ┌─────────┐                                  │
│  │ badge   │  "N lots available"              │
│  └─────────┘                                  │
│                                               │
│  H1: Project Name — City, Country             │
│  P:  One-line value proposition               │
│                                               │
│  ┌──────────────────────┐                     │
│  │  FORM CARD           │                     │
│  │  ─────────────────   │                     │
│  │  Name                │                     │
│  │  Phone (WhatsApp)    │                     │
│  │  Interest [dropdown] │                     │
│  │  [CTA Button]        │                     │
│  │  privacy note        │                     │
│  └──────────────────────┘                     │
│                                               │
└──────────────────────────────────────────────┘
```

- Video: drone footage, auto-playing, muted, looped. Fallback: hero photo.
- Overlay: `var(--hero-overlay)` — dark enough for white text, light enough to see the property.
- Badge: pill shape, `backdrop-filter: blur(4px)`, semi-transparent white background.
- Form card: white, `border-radius: 12px`, `box-shadow: 0 12px 40px rgba(0,0,0,0.18)`. Max width 440px. Floats over the hero.

### Form

- 3 fields only. Name, phone, interest dropdown.
- Inputs: `padding: 12px`, `border: 1px solid var(--line)`, `border-radius: 8px`, `font-size: 16px` (prevents iOS zoom).
- Focus state: `outline: 2px solid var(--accent)`.
- CTA button: full width, `padding: 14px`, `background: var(--accent)`, `color: white`, `border-radius: 8px`, `font-weight: 600`.
- Disabled state: `opacity: 0.6`, `cursor: not-allowed`.
- Error: `color: var(--error)`, below the button.
- Privacy note: `--text-xs`, `var(--muted)`.

### Cards

```css
.card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: var(--space-lg);
  transition: box-shadow 0.15s ease;
}
.card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.06);
}
```

Used for: selling points, testimonials, timeline, contact info.

### Stat cards (selling points)

```
┌─────────────┐
│  89          │  ← var(--accent), --text-3xl, --font-bold
│  Dev. lots   │  ← var(--muted), --text-base
└─────────────┘
```

3-column grid on desktop, stack on mobile.

### Testimonials

```
┌───────────────────────────────────────┐
│  [avatar]  "Quote text here."         │
│            — Name, Month              │
└───────────────────────────────────────┘
```

- Avatar: 48px circle, `object-fit: cover`. Use real photos when available.
- Quote: italic, `var(--fg)`.
- Attribution: `var(--muted)`, `--text-sm`.

### FAQ accordion

- `<details>` element (native, no JS).
- `<summary>`: `--font-semibold`, pointer cursor.
- Content: `var(--muted)`, `--space-sm` top margin.
- Each item: white card, `1px solid var(--line)`, `border-radius: 12px`, `--space-md --space-lg` padding.

### Mobile sticky CTA

```
┌───────────────────────────────────────┐
│  [WhatsApp ███]     [Call ███]        │
└───────────────────────────────────────┘
```

- Fixed bottom, shows only below 720px.
- WhatsApp: `background: var(--whatsapp)`.
- Call: `background: var(--accent)`.
- Both: white text, `border-radius: 8px`, `--font-semibold`.
- Parent: white background, top border, `padding: 10px 12px`.

## Photography direction

The strongest performing RE landing pages use:

1. **Hero**: Aerial/drone shot showing the full development + surrounding area. This builds credibility — you can see the roads, the infrastructure, the context. Avoid detail shots for the hero.
2. **Selling points**: Ground-level photos of completed infrastructure (roads, utilities, model homes). This proves progress.
3. **Amenities**: Photos of nearby amenities with the property visible in context (beach + property, mountain + property). Not stock photos.
4. **Testimonials**: Real buyer photos. If unavailable, use initials in colored circles — never stock headshots.
5. **Lot map**: If available, an interactive or annotated lot map converts higher than any other visual element.

Never use: stock photography of happy families, sunset silhouettes, AI-generated property renders (unless explicitly labeled "artist rendering").

## Responsive breakpoints

```css
/* Mobile-first. 65%+ of Meta ad traffic is mobile. */
@media (min-width: 720px)  { /* tablet+: 2-col grids, side-by-side layouts */ }
@media (min-width: 1024px) { /* desktop: 3-col grids, wider containers */ }
```

- Form card: below 720px, full-width with `border-radius: 0` at the bottom of the hero.
- Stat grid: `repeat(auto-fit, minmax(240px, 1fr))`.
- Hero height: `min-height: 80vh` on desktop, `min-height: 70vh` on mobile.

## Animation

Minimal. This is not a portfolio site.

- Page load: no entrance animations. Content renders immediately.
- Form interactions: `transition: border-color 0.15s ease` on focus.
- Card hover: `transition: box-shadow 0.15s ease`.
- Hero video: autoplay, no play button. If video fails to load, fall back to static image.
- Scroll: no parallax, no scroll-triggered animations. They compete with the video and slow down mobile.

## Accessibility

- All text on hero overlay: minimum 4.5:1 contrast ratio against the darkest overlay point.
- Form labels: explicit `<label for="...">` on every input.
- Focus states: visible `outline` on all interactive elements.
- Images: `alt` text on every `<img>`. Hero video: `aria-hidden="true"` (decorative).
- Mobile CTA: `aria-label="Quick contact"` on the nav container.
- Semantic HTML: `<header>`, `<main>`, `<section>`, `<footer>`, `<nav>`.

## Performance targets

- First Contentful Paint: < 1.5s
- Largest Contentful Paint: < 2.5s (hero video poster loads first)
- Total page weight: < 500KB excluding video
- No external CSS frameworks (no Tailwind, no Bootstrap — inline styles or `<style>` block)
- No external JS dependencies
- Fonts: system stack only (zero font downloads)
- Video: serve WebM with MP4 fallback. Lazy-load if below fold.

## What this file does NOT cover

- Thank-you page (`site/thank-you.html`) — uses the same tokens but has its own layout. See the file directly.
- Email templates — follow-up emails use plain text (WhatsApp-first system).
- Ad creative — managed by `skills/ad-creative/SKILL.md`, not this design system.
