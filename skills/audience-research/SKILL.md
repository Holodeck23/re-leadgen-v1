---
name: audience-research
description: "Research and build Meta ad targeting from property data alone. Use when launching a new campaign or when reflective-ops recommends audience expansion. Produces a targeting spec (interests, behaviors, demographics, locations, exclusions) compliant with Meta Special Ad Category: Housing. Reads property-context and scoring-model segments. Never requires prior ads experience from the user."
user-invokable: true
---

# Audience Research — targeting from property data

You build Meta ad audiences from scratch using only the property context and scoring model. The user has zero ads experience — never ask them to pick interests or configure targeting manually.

## Before starting

1. Invoke `property-context` skill. STOP if BLOCKED.
2. Read `data/scoring-model.json` → `audience_segments` for segment definitions (investor, homebuyer, retiree, expat).
3. Read `data/kill-scale-rules.json` for budget context.

## Special Ad Category: Housing (non-negotiable)

All real estate ads on Meta fall under **Special Ad Category: Housing**. This restricts targeting:

- **Age**: 18–65+ only (no narrowing below 18 or above 65)
- **Gender**: All genders (no gender targeting)
- **ZIP code**: Cannot target specific ZIP/postal codes
- **Location radius**: Minimum 15-mile (25 km) radius
- **Excluded interests**: Cannot use demographics like income, net worth, home ownership status, credit history
- **Lookalike**: Must use "Special Ad Audience" (not standard Lookalike)

Violating these rules causes ad rejection or account restriction. Every targeting spec you produce MUST comply.

## Process

### Step 1 — Extract targeting signals from property data

Read the property context and extract:

| Signal | Source field | Targeting implication |
|--------|-------------|---------------------|
| Location | `location.city`, `location.region`, `location.country` | Geo-targeting center point |
| Price range | `inventory.lots.price_range`, `inventory.complex_units.price_range` | Interest-based proxies (luxury travel, investment forums, etc.) |
| Key selling points | `key_selling_points[]` | Interest categories (golf → golf interest, beach → water sports, etc.) |
| Target audiences | `target_audiences[]` | Segment-specific interest stacks |
| Amenities | `amenities[]` | Lifestyle interest signals |
| Timeline | `timeline.phase_1`, `timeline.completion` | Urgency framing (not targeting, but copy angle) |

### Step 2 — Build interest stacks per segment

For each segment in `scoring-model.json.audience_segments`, build an interest stack:

**Investor segment:**
- Real estate investing, Property investment, Real estate crowdfunding
- Entrepreneurship, Small business owners
- Financial planning, Wealth management
- "Competitor" interests: Fundrise, Arrived Homes, Roofstock (if applicable)
- Life events: Recently started a business (if available)

**Homebuyer segment:**
- Home improvement, Interior design, Architecture
- Family-oriented: Parenting, Education, School districts
- Life events: Recently moved, Newly married, New job
- Lifestyle interests matching amenities (e.g., hiking if near mountains)

**Retiree segment:**
- Retirement planning, AARP, Senior living
- Leisure: Golf, Gardening, Travel, Cruise
- Healthcare: Wellness, Medical tourism (if applicable)
- Geographic: Expat communities, Snowbird destinations

**Expat segment:**
- International relocation, Expat communities, Digital nomad
- Residency by investment, Second passport
- Remote work, Freelancing
- Country-specific expat groups

### Step 3 — Build behavioral layers

Layer behavioral signals (Housing-compliant) on top of interests:

- **Engaged shoppers** (broad, but useful as AND condition)
- **Frequent travelers** (for international property)
- **Technology early adopters** (correlates with higher income without targeting income directly)
- **Small business owners** (proxy for financial capacity)

### Step 4 — Build location targeting

From `property.json.location`:

1. **Primary radius**: 15-mile minimum around the property location (for local buyers)
2. **Feeder cities**: Major metros within the property's country (domestic investors/relocators)
3. **International markets** (if property targets expats): Key source countries (US, Canada, UK for LATAM property; UK, Germany for Southern Europe, etc.)

Output a location spec:
```json
{
  "primary": { "lat": 0.0, "lng": 0.0, "radius_miles": 25 },
  "feeder_cities": ["City A", "City B"],
  "international": ["Country A", "Country B"],
  "exclusions": []
}
```

### Step 5 — Cold-start targeting strategy

For brand-new accounts with zero conversion data:

**Hybrid approach (recommended):**
- **60% budget → Manual targeting** (3 ad sets, one per top segment):
  - Each ad set: segment-specific interests + location + behavioral layers
  - $20–50/day per ad set (from `kill-scale-rules.json`)
  - ABO (Ad Set Budget Optimization) — keep spend per-variant visible

- **40% budget → Advantage+ audience** (1 ad set):
  - Broad targeting with Meta's algorithm
  - Audience suggestions seeded from your interest stacks (not restrictions)
  - Let Meta find patterns you didn't anticipate

**Why hybrid:** Manual targeting gives you readable data on which segments convert. Advantage+ often finds cheaper leads but you can't see WHY they converted. Run both; once you have 30–50 conversion events, Advantage+ improves dramatically and you can shift budget toward it.

**Life-event targeting (highest intent, Housing-compliant):**
- Recently moved
- Newly married / Recently engaged
- New job
- These are the strongest cold-start signals for real estate. Include in at least one ad set.

### Step 6 — Retargeting audiences (day-1 setup)

Even before any ads run, set up these custom audiences so the Pixel populates them:

1. **Website visitors (all)** — 180-day window
2. **Landing page visitors** — 30-day window
3. **Form starters who didn't submit** — 14-day window
4. **Video viewers (25%, 50%, 75%)** — 30-day window (if running video ads)
5. **Engaged with FB/IG page** — 90-day window

These start empty but begin populating the moment ads go live.

### Step 7 — Exclusion audiences

**External Exclusions (Mandatory):**
- People who already submitted a lead form (customer list or Pixel event `Lead`)
- Current customers (if a list is available)
- Existing contacts from the CRM sheet

**Internal Competition Guard (Self-Bidding Protection):**
- **Broad Exclusion**: In the 3 Manual ad sets, exclude the broad audience defined in the Advantage+ ad set if possible (e.g. by using the Advantage+ seed interests as exclusions in manual sets).
- **Segment De-duplication**: If interests overlap heavily between segments (e.g. "home improvement" and "investor"), use exclusions to ensure the Manual ad sets are as distinct as possible. 
- **Goal**: Minimize internal bidding overlap so you aren't paying more to show two different ads to the same person.

## Output format

Produce a `targeting_spec` for each ad set:

```json
{
  "ad_set_name": "INV_manual_interest-investment-realestate",
  "segment": "investor",
  "strategy": "manual",
  "special_ad_category": "HOUSING",
  "location": {
    "type": "radius",
    "center": "City, Country",
    "radius_miles": 25,
    "feeder_cities": ["Metro A", "Metro B"]
  },
  "interests": [
    { "name": "Real estate investing", "id": "TBD_at_launch" },
    { "name": "Property investment", "id": "TBD_at_launch" }
  ],
  "behaviors": ["Small business owners"],
  "life_events": [],
  "age_min": 18,
  "age_max": 65,
  "gender": "all",
  "custom_audiences_exclude": ["lead_form_submitters"],
  "daily_budget_usd": 30,
  "notes": "Housing-compliant. Investor segment, manual targeting, interest-stacked."
}
```

Also produce a summary table:

```
| Ad Set | Segment | Strategy | Daily Budget | Est. Audience Size | Key Interests |
|--------|---------|----------|-------------|-------------------|---------------|
| INV_manual | investor | manual | $30 | 500K–1.5M | RE investing, property, business |
| HB_manual | homebuyer | manual | $30 | 800K–2M | Home improvement, family, life events |
| RET_manual | retiree | manual | $25 | 300K–900K | Retirement, golf, travel |
| BROAD_adv | all | advantage+ | $40 | broad | Meta-optimized, seeded |
```

## Validation checklist (run before returning)

- [ ] Special Ad Category: Housing declared on every ad set
- [ ] No age narrowing below 18 or above 65
- [ ] No gender targeting
- [ ] No ZIP code targeting
- [ ] Location radius ≥ 15 miles
- [ ] No income/net-worth/credit-score interests
- [ ] Total daily budget ≤ `kill-scale-rules.json.targets.daily_budget_cap_usd`
- [ ] At least one retargeting audience defined
- [ ] At least one life-event targeting layer included
- [ ] Every interest name is real (verifiable via Meta Ads API `mcp__meta-ads__search_targeting`)

## Files this skill reads

- `data/property.json` (via property-context)
- `data/scoring-model.json` — segment definitions
- `data/kill-scale-rules.json` — budget constraints
- Meta Ads MCP — `search_targeting` to validate interest IDs

## Related skills

- `campaign-launch` — consumes this skill's output to actually create campaigns
- `paid-ads` — manages campaigns after launch
- `ad-creative` — generates the ads that go into these audiences
