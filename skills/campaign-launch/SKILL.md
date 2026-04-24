---
name: campaign-launch
description: "End-to-end campaign creation for users with zero ads experience. Takes populated property data and produces live Meta campaigns — audience research, creative generation, campaign structure, Pixel verification, and launch with learning-phase guardrails. The user's only job is to approve the final plan. Use when going from 'property data ready' to 'ads running.' For ongoing management after launch, see reflective-ops."
user-invokable: true
---

# Campaign Launch — from property data to live ads

You take a user who has never run an ad and get them to live, optimized Meta campaigns. Every decision is explained. Nothing launches without explicit approval.

## Prerequisites (halt if any fail)

1. `data/property.json` populated — invoke `property-context`, STOP if BLOCKED.
2. `.env` has `GOOGLE_SHEETS_KEY_FILE`, `LEAD_SHEET_ID`, `ANTHROPIC_API_KEY`.
3. Meta Ads MCP is connected — test with `mcp__meta-ads__get_ad_account` (or equivalent list call). If auth fails, tell user to refresh at https://pipeboard.co/api-tokens.
4. Landing page is deployed and form is working (check: `site/index.html` has no `REPLACE_WITH_` placeholders).
5. Pixel is installed — confirm via `mcp__meta-ads__get_pixels` or by checking the landing page source.

If any prerequisite fails, print exactly what's missing and how to fix it. Do not proceed.

## The 9-step sequence

### Step 1 — Validate property data completeness

Read `data/property.json` and check every required field:

```
project_name          — non-empty, no UPDATE
location.country      — non-empty
location.region       — non-empty
location.city         — non-empty
location.description  — non-empty, ≥20 chars
inventory.lots        — at least total + price_range
inventory.complex_units — at least total + price_range (or explicitly null if N/A)
key_selling_points    — array, ≥3 items, each ≥10 chars, no filler
target_audiences      — array, ≥2 items, each has id + hook + budget_range
amenities             — array, ≥3 items
timeline.phase_1      — non-empty
media.photos          — at least 3 URLs (or paths)
media.drone_video     — URL or null (note if missing — video ads need this)
contact.sales_name    — non-empty
contact.sales_phone   — non-empty
contact.sales_whatsapp — non-empty
```

Also verify the landing page is deployed and looks right. If `property.json` has a `branding.accent_color` field, note it — it can override the default gold accent in `site/DESIGN.md`.

Print a checklist. If anything is missing, tell the user exactly what to add and STOP.

### Step 2 — Pixel and CAPI health check

Run the `ads-meta` skill's Pixel/CAPI subset (checks 1–15 of its 50-check audit):

1. Pixel fires on landing page load (PageView event)
2. Pixel fires on form submission (Lead event)
3. CAPI is sending server-side Lead events (via `form-handler.gs`)
4. Event deduplication is working (event_id matches between browser and server)
5. Domain verification status

If Pixel is not firing, walk the user through fixing it before proceeding.

### Step 3 — Audience research

Invoke the `audience-research` skill. It produces:
- 3 manual-targeting ad sets (one per top segment from scoring-model)
- 1 Advantage+ ad set (broad, algorithm-optimized)
- Retargeting audience definitions (empty now, populate with traffic)
- Exclusion audiences

Present the targeting plan to the user in plain language:

```
Here's who we're targeting and why:

1. INVESTORS ($30/day) — People interested in real estate investing,
   property investment, and small business. Located in [feeder cities].
   Why: Your property's [selling point] appeals to ROI-focused buyers.

2. HOMEBUYERS ($30/day) — People interested in home improvement,
   recently married or moved, in [locations].
   Why: [selling point about lifestyle/family].

3. [SEGMENT 3] ($25/day) — ...

4. BROAD TEST ($40/day) — Meta's algorithm picks the audience.
   We seed it with our best guesses but let Meta optimize.
   Why: Often finds buyers we didn't think to target.

Total daily budget: $125 (your cap is $300 — leaves room to scale winners)

Does this look right? I can adjust segments, locations, or budgets.
```

Wait for approval before proceeding.

### Step 4 — Generate launch creative

**Optional but recommended: competitive research first.**

Ask the user: "Want to check what competitors are running before we generate ads? It takes 5 minutes and helps us avoid angles that are oversaturated and find patterns that are proven to work."

If yes, invoke `competitive-intel` skill:
1. Guide the user to the Meta Ad Library with search terms relevant to their property/market
2. Analyze whatever they paste back (ad copy, screenshots, URLs)
3. Produce a pattern report and 3–6 inspiration seeds
4. Use the seeds to inform the creative generation below

If no or if the user wants to move fast, proceed directly with `ad-creative`.

Invoke `ad-creative` skill in "from scratch" mode with these enhancements:

**Hook categories (at least one ad per category):**

| Category | Psychology | Example pattern |
|----------|-----------|----------------|
| Curiosity gap | Information gap theory — brain needs closure | "Most people don't know this about [location]..." |
| Social proof | Bandwagon / authority bias | "[X] lots sold in [timeframe]. Here's what buyers saw." |
| Specificity | Concrete > abstract in memory + trust | "[Exact lot size] with [exact amenity] — $[exact price]" |
| Loss aversion | Fear of missing > desire to gain | "[N] lots left at phase-1 pricing. Phase 2 is [X]% higher." |
| Identity | Self-concept → aspiration match | "Built for people who [identity statement from audience hook]" |
| Pattern interrupt | Novelty captures attention in feed scroll | Lead with unexpected fact, drone angle, or question |

**Output per generation run:**
- 2 Feed ads (different segments, different hook categories)
- 2 Reels/Stories ads (vertical 9:16, hook in first 1 second)
- 1 Carousel ad (3–5 cards: hero → selling points → social proof → CTA)
- 1 Retargeting ad (for site visitors — assumes they've seen the property already)

Each ad includes: segment, hook category, primary text (≤125 chars visible), headline (≤40 chars), description (≤30 chars), CTA button, image/video reference from `property.json.media`.

Write approved variants to `data/creative-library.jsonl` (one JSON object per line, `status: "approved"`).

Present all 6 ads to the user for review. Explain the psychology behind each.

### Step 5 — Build campaign structure

Design the Meta campaign hierarchy:

```
Campaign: {project_name} — Lead Gen
├── Ad Set: INV_manual (investor segment, manual targeting)
│   ├── Ad: Feed — curiosity hook
│   └── Ad: Reels — specificity hook
├── Ad Set: HB_manual (homebuyer segment, manual targeting)
│   ├── Ad: Feed — social proof hook
│   └── Ad: Reels — identity hook
├── Ad Set: [SEGMENT3]_manual
│   ├── Ad: Carousel — multi-selling-point
│   └── Ad: Feed — loss aversion hook
└── Ad Set: BROAD_advantage_plus
    ├── Ad: Feed — best-performing hook from above
    └── Ad: Reels — second-best hook

Campaign: {project_name} — Retargeting
└── Ad Set: RETARGET_site_visitors (14-day window)
    └── Ad: retargeting variant
```

**Naming convention:**
- Campaign: `{project_name}_leadgen_YYYYMMDD`
- Ad set: `{SEGMENT}_{strategy}_{primary_interest}`
- Ad: `{format}_{hook_category}_{variant_id}`

**Settings for every campaign:**
- Special Ad Category: `HOUSING`
- Objective: `OUTCOME_LEADS`
- Optimization: `OFFSITE_CONVERSIONS` → `Lead` event
- Destination: Landing page URL
- Budget: ABO (Ad Set Budget Optimization) for test phase
- Bid strategy: Lowest cost (let Meta optimize while learning)
- Placements: Automatic (Meta distributes across FB Feed, IG Feed, Stories, Reels)

Present the full structure to the user. Wait for approval.

### Step 6 — Pre-launch checklist

Run through every item. Must all pass:

```
PROPERTY DATA
  ✓ property.json complete — no UPDATE placeholders
  ✓ At least 3 photos available
  ✓ Sales contact info populated

TRACKING
  ✓ Meta Pixel installed on landing page
  ✓ PageView event fires on page load
  ✓ Lead event fires on form submit
  ✓ CAPI sending server-side events
  ✓ Event dedup working (matching event_ids)
  ✓ UTM parameters configured in ad URLs

LANDING PAGE
  ✓ Form submits successfully
  ✓ Data appears in Google Sheet
  ✓ Thank-you page loads after submission
  ✓ Page loads in <3 seconds
  ✓ Mobile-responsive

META ADS ACCOUNT
  ✓ Ad account accessible via Pipeboard MCP
  ✓ Payment method on file
  ✓ No policy violations or restrictions
  ✓ Domain verified (or verification in progress)

CAMPAIGN SETUP
  ✓ Special Ad Category: Housing selected
  ✓ Pixel connected to ad account
  ✓ Custom conversions configured (Lead event)
  ✓ All ad creative reviewed and approved by user
  ✓ Total daily budget within cap ($300)
  ✓ URL parameters include adset_id={{adset.id}} + UTMs
```

If anything fails, fix it or explain how to fix it. Do not proceed until all pass.

### Step 7 — Create campaigns via Meta Ads API

Execute via Pipeboard MCP tools:

1. Create campaign(s) with `mcp__meta-ads__create_campaign`:
   - `special_ad_categories: ["HOUSING"]`
   - `objective: "OUTCOME_LEADS"`
   - `status: "PAUSED"` (launch paused, review first)

2. Create ad sets with `mcp__meta-ads__create_adset`:
   - Targeting from audience-research output
   - Budget from plan
   - Optimization goal: `OFFSITE_CONVERSIONS`
   - Pixel + Lead event configured
   - Schedule: start immediately when unpaused
   - URL parameters: `adset_id={{adset.id}}&utm_source=facebook&utm_medium=paid&utm_campaign={{campaign.name}}&utm_content={{ad.name}}`

3. Create ad creatives with `mcp__meta-ads__create_ad_creative`:
   - Copy from creative-library.jsonl
   - Image/video from property.json media URLs
   - Landing page URL as destination

4. Create ads with `mcp__meta-ads__create_ad`:
   - Link creative to ad set
   - Status: PAUSED

Log every API call result. If any call fails, halt and report the error.

### Step 8 — Write launch config

Create `data/launch-config.json`:

```json
{
  "version": 1,
  "launched_at": "2026-04-24T14:00:00Z",
  "launched_by": "campaign-launcher",
  "campaigns": [
    {
      "campaign_id": "...",
      "campaign_name": "...",
      "ad_sets": [
        {
          "adset_id": "...",
          "adset_name": "...",
          "segment": "investor",
          "strategy": "manual",
          "daily_budget_usd": 30,
          "ads": ["ad_id_1", "ad_id_2"]
        }
      ]
    }
  ],
  "total_daily_budget_usd": 125,
  "learning_phase": {
    "start_date": "2026-04-24",
    "min_end_date": "2026-05-08",
    "target_events_for_exit": 50,
    "events_so_far": 0,
    "status": "active"
  },
  "do_not_edit_until": "2026-05-08",
  "do_not_edit_reason": "Learning phase — Meta's algorithm needs 14 days and ~50 Lead events to optimize delivery. Editing audiences, budgets >20%, or creative during this window resets the learning phase. The reflective-ops loop will respect this date and limit actions to pause-only for underperformers.",
  "audience_research_snapshot": {},
  "creative_library_snapshot": [],
  "notes": "First launch. Hybrid cold-start: 60% manual + 40% Advantage+."
}
```

### Step 9 — Go live

Present the final summary to the user:

```
READY TO LAUNCH

Campaigns created (currently PAUSED):
  1. {project_name} — Lead Gen
     - 4 ad sets, 8 ads
     - Total daily budget: $125
  2. {project_name} — Retargeting
     - 1 ad set, 1 ad
     - Daily budget: $15

Estimated first leads: 24–72 hours after launch
Learning phase: 14 days (do not make major changes during this period)

The daily operations loop (reflective-ops) will:
  - Monitor performance every morning
  - Score and route every lead
  - Pause underperformers automatically
  - Alert you to hot leads within 2 hours
  - Send you a daily briefing

Say "launch" to unpause all campaigns and go live.
Say "review [ad set name]" to look at a specific ad set first.
Say "adjust [what]" to change something before launching.
```

When the user says "launch":
1. Unpause all campaigns and ad sets via MCP
2. Log the launch event to `data/ad-history.jsonl`
3. Git commit: `ops: YYYY-MM-DD campaign launch — N campaigns, N ad sets, $X daily budget`
4. Print confirmation with the Meta Ads Manager URL to view campaigns

## Learning-phase guardrails

Write these to `data/launch-config.json` and `reflective-ops` respects them:

- **First 14 days after launch:**
  - No audience changes
  - No budget changes >20% per ad set
  - No creative rotation (unless an ad is clearly failing: CTR <0.005 after $50 spend)
  - No switching between ABO and CBO
  - Pausing is allowed (kill rules still apply)
  
- **After 14 days OR 50 Lead events (whichever comes first):**
  - Full reflective-ops loop activates
  - Scale/kill/refresh decisions run normally
  - CBO consolidation becomes available when ≥2 winning ad sets emerge

## Error recovery

If the process fails at any step:
1. Log what succeeded and what failed
2. Save partial progress to `data/launch-config.json` with `"status": "incomplete", "failed_at_step": N`
3. Print clear instructions for the user
4. The process can be re-run — it checks for existing campaigns and resumes from the failure point

## Files this skill reads / writes

- **Reads:** `data/property.json` (via property-context), `data/scoring-model.json`, `data/kill-scale-rules.json`, `data/creative-library.jsonl`, Meta Ads MCP
- **Writes:** `data/creative-library.jsonl` (approved variants), `data/launch-config.json` (new file), `data/ad-history.jsonl` (launch event), git commits

## Related skills

- `audience-research` — called in Step 3 for targeting
- `competitive-intel` — optionally called before Step 4 to research competitor patterns and seed creative
- `ad-creative` — called in Step 4 for creative generation
- `ads-meta` — called in Step 2 for Pixel health check
- `paid-ads` — manages campaigns post-launch
- `reflective-ops` — takes over daily management after launch
