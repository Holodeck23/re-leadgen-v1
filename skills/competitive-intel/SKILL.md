---
name: competitive-intel
description: "Analyze competitor ad creative from the Meta Ad Library to identify winning patterns, hook types, and copy structures, then feed insights into ad-creative for inspiration. Use when the user says 'what are competitors running,' 'ad inspiration,' 'competitive analysis,' 'spy on ads,' 'what's working in the market,' or provides competitor ad copy/screenshots to analyze. Works with user-provided data (copy-paste, URLs, screenshots) and the public Meta Ad Library."
user-invokable: true
---

# Competitive Intel — learn from what's working in the market

You analyze competitor real estate ads to find winning patterns, then feed those patterns into the creative pipeline. You never copy — you extract the underlying psychology and adapt it with real property data.

## Before starting

1. Invoke `property-context` skill. STOP if BLOCKED. You need to know what you're selling to judge relevance.
2. Read `data/scoring-model.json` → `audience_segments` for your target segments.
3. Read `data/creative-library.jsonl` to see what you've already generated (avoid duplicating angles).
4. If performance data exists, read `data/ad-history.jsonl` (last 20 entries) to know what's working and what isn't for your own campaigns.

## Data sources (in order of reliability)

### Source 1: Meta Ad Library (primary — free, public, legal)

The Meta Ad Library (https://www.facebook.com/ads/library) is a public transparency tool. Any active ad on Facebook or Instagram is visible.

**How to use it:**

Tell the user:
```
Go to https://www.facebook.com/ads/library

1. Set country to [property's target market from property.json]
2. Set category to "All ads"
3. Search for competitors by name, or search keywords like:
   - "[city/region] real estate"
   - "[city/region] lots for sale"
   - "[city/region] property investment"
   - "development lots [country]"
   - "new homes [region]"

4. For each interesting ad, copy:
   - The primary text (the main ad copy)
   - The headline (below the image)
   - How long it's been running (longer = probably working)
   - The format (image, video, carousel)
   - The landing page URL (visible in the ad)

Paste what you find here and I'll analyze the patterns.
```

**What the Ad Library shows:** active ads, ad copy, images/video thumbnails, start date, page name, platform (FB/IG), format.

**What it does NOT show:** performance metrics (CTR, CPL, conversions), audience targeting, budget, engagement counts. A long-running ad is the best proxy for "this is working" — advertisers don't keep paying for ads that don't convert.

### Source 2: User-provided competitor data

The user may paste ad copy, share screenshots, or provide URLs. Accept any format:
- Raw ad text (primary text + headline + description)
- Screenshots of ads (describe what you see)
- Landing page URLs (analyze the offer, angle, CTA)
- Ad Library URLs (extract the visible data)

### Source 3: Own account performance data

Via the Pipeboard MCP (`mcp__meta-ads__*`), pull insights from your own campaigns. This is the only source with real performance metrics. Use it to compare your patterns against competitors' patterns.

## Analysis framework

For every competitor ad collected, produce a structured analysis:

### Step 1 — Classify the ad

```json
{
  "competitor": "Page Name",
  "ad_id_or_ref": "description or Ad Library reference",
  "running_since": "YYYY-MM-DD or approximate",
  "format": "image | video | carousel | collection",
  "platform": "facebook | instagram | both",
  "hook_category": "curiosity_gap | social_proof | specificity | loss_aversion | identity | pattern_interrupt | other",
  "angle": "investment_roi | lifestyle | scarcity | location | price | community | luxury | ...",
  "segment_target": "investor | homebuyer | retiree | expat | generic",
  "primary_text": "exact copy or summary",
  "headline": "exact copy",
  "description": "exact copy if visible",
  "cta_button": "Learn More | Sign Up | Get Offer | ...",
  "landing_page_url": "if visible",
  "visual_description": "what the image/video shows",
  "running_duration_days": 0,
  "longevity_signal": "short (<7d) | medium (7-30d) | long (30-90d) | evergreen (90d+)"
}
```

### Step 2 — Extract patterns across all collected ads

After classifying 5+ ads, produce a pattern report:

```
COMPETITIVE PATTERN REPORT
==========================

Ads analyzed: {n}
Competitors found: {n}
Date range: {earliest} to {latest}

HOOK DISTRIBUTION
  Curiosity gap:    ███░░  3/10 (30%)
  Social proof:     ██░░░  2/10 (20%)
  Specificity:      ████░  4/10 (40%)
  Loss aversion:    █░░░░  1/10 (10%)
  Identity:         ░░░░░  0/10 (0%)
  Pattern interrupt: ░░░░░  0/10 (0%)

ANGLE DISTRIBUTION
  Investment ROI:   ████░  40%
  Lifestyle:        ██░░░  20%
  Scarcity:         ██░░░  20%
  Price:            █░░░░  10%
  Location:         █░░░░  10%

SEGMENT TARGETING
  Investor:         ████░  40%
  Homebuyer:        ███░░  30%
  Generic:          ██░░░  20%
  Retiree:          █░░░░  10%

LONGEST-RUNNING ADS (likely winners)
  1. [Competitor A] — "headline..." — 87 days — specificity hook, investment angle
  2. [Competitor B] — "headline..." — 54 days — social proof hook, lifestyle angle
  3. ...

COPY PATTERNS IN TOP ADS
  - Average primary text length: {n} chars
  - Most common CTA: {cta}
  - Numbers in headline: {pct}% of top ads use specific numbers
  - Question in hook: {pct}% start with a question
  - Price mentioned: {pct}% mention price in primary text
  - Urgency language: {pct}% use scarcity/urgency

VISUAL PATTERNS
  - Drone/aerial: {pct}%
  - Property interior: {pct}%
  - Lifestyle/people: {pct}%
  - Map/location: {pct}%
  - Infographic/stats: {pct}%

GAP ANALYSIS (vs your creative library)
  Hooks you haven't tested: [list]
  Angles competitors use that you don't: [list]
  Segments competitors target that you don't: [list]
  Copy patterns you could adapt: [list]
```

### Step 3 — Generate inspiration seeds

For each identified gap, produce an **inspiration seed** — NOT a copy of the competitor's ad, but an adaptation using your property data:

```json
{
  "inspired_by": "Competitor A — specificity hook, 87-day evergreen",
  "insight": "Competitor leads with exact lot size + exact price. Their longest-running ad is pure specificity.",
  "adaptation": {
    "hook_category": "specificity",
    "angle": "investment_roi",
    "segment": "investor",
    "primary_text_draft": "[Exact lot size from property.json] with [real amenity] — $[real price]. [Real fact about appreciation/ROI].",
    "headline_draft": "[Real number] lots from $[real price]",
    "why_this_works": "Specificity builds trust. The competitor proved this hook survives 87 days of spend — it converts."
  },
  "anti_copy_check": "Uses our property facts, not theirs. Different phrasing, same psychology."
}
```

Generate 3–6 inspiration seeds per analysis run. Each must:
- Use facts exclusively from `property-context` (never the competitor's facts)
- Reference a different hook category or angle than your existing creative library
- Explain the psychological principle (not just "this looked good")
- Pass the anti-slop rules from CLAUDE.md

### Step 4 — Feed into the creative pipeline

Present inspiration seeds to the user for review. On approval:

1. Pass seeds to `ad-creative` skill as starting points for a full generation run
2. The `ad-creative` skill expands each seed into proper Meta ad specs (primary text ≤125 chars, headline ≤40 chars, etc.)
3. Approved variants write to `data/creative-library.jsonl`

## Competitive monitoring cadence

Recommend the user check the Ad Library:
- **Before first launch**: collect 10–20 competitor ads to seed initial creative
- **Weekly (Friday review)**: 5-minute scan for new competitor ads, especially long-runners
- **After a creative refresh**: check if competitors are running similar angles (convergent evolution = the angle works)
- **When CPL rises**: competitors may have saturated an angle; check what they switched to

## What NOT to do

- **Never copy ad text verbatim.** Extract the pattern, adapt with your data.
- **Never scrape the Ad Library programmatically.** It violates Meta's ToS and gets accounts flagged. The public web interface is the approved access method.
- **Never assume a long-running ad is a winner.** It's the best proxy available, but some advertisers are lazy. Cross-reference with common sense.
- **Never invent competitor performance data.** You can see their ads; you cannot see their metrics. Say "this ad has run for 60 days, which suggests it's performing" — never "this ad gets a 2% CTR."
- **Never target the same audiences as competitors based solely on their ad copy.** Your `audience-research` skill already builds targeting from your property data. Use competitive intel for creative inspiration, not targeting decisions.

## Output format

Two deliverables per run:

1. **Pattern Report** (the analysis — see Step 2 template)
2. **Inspiration Seeds** (the actionable output — see Step 3 template)

Present both to the user. The pattern report builds understanding; the seeds build campaigns.

## Files this skill reads

- `data/property.json` (via property-context) — facts for adaptation
- `data/scoring-model.json` — segment definitions
- `data/creative-library.jsonl` — existing creative (for gap analysis)
- `data/ad-history.jsonl` — own performance patterns (for comparison)

## Files this skill writes

- Nothing directly. Inspiration seeds feed into `ad-creative`, which writes to `data/creative-library.jsonl`.

## Related skills

- `ad-creative` — consumes inspiration seeds to generate full ad specs
- `audience-research` — targeting decisions (not influenced by competitive intel)
- `campaign-launch` — may invoke this skill in Step 4 to seed initial creative
- `reflective-ops` — weekly cadence may trigger a competitive scan recommendation
