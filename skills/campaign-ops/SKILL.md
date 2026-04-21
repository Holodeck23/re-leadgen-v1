---
name: re-campaign-ops
description: Full FB/IG campaign lifecycle — launch, monitor, optimize, A/B test, kill underperformers
---

# Campaign Operations

Manage the full lifecycle of Facebook and Instagram ad campaigns for the property listing.
Requires Meta Ads MCP server to be connected.

## Campaign Structure

```
Campaign (OUTCOME_LEADS objective)
├── Ad Set: Investors — US (interest targeting)
├── Ad Set: Investors — Expat communities (lookalike)
├── Ad Set: Homebuyers — Regional (geo + interest)
└── Ad Set: Retargeting — Site visitors
    └── Ads: 2-3 variations per ad set (for A/B testing)
```

## Commands

### Launch New Campaign

When asked to launch a campaign:

1. Read `data/property.json` for listing details
2. Use `skills/ad-copy/` to generate ad variations
3. Create the campaign via MCP:
   - `mcp_meta_ads_create_campaign` with objective `OUTCOME_LEADS`
   - `mcp_meta_ads_create_adset` for each audience segment
   - `mcp_meta_ads_create_ad_creative` for each ad variation
   - `mcp_meta_ads_create_ad` to attach creatives to ad sets
4. Set daily budget (recommend starting at $20-50/day per ad set)
5. Output a summary of what was created

Before creating anything, show the user the full plan and get confirmation.

### Check Performance

When asked to check performance or "how are the ads doing":

1. `mcp_meta_ads_get_campaigns` to list active campaigns
2. `mcp_meta_ads_get_insights` for each campaign (last 7 days default)
3. Report in this format:

```
## Campaign Performance — [date range]

**Cost per Lead: $X.XX** (target: under $Y)
Total Spend: $X | Leads: N | CTR: X% | CPM: $X

### By Ad Set
| Ad Set | Spend | Leads | CPL | CTR | Frequency |
|--------|-------|-------|-----|-----|-----------|

### By Ad (top 5)
| Ad | Impressions | Clicks | CTR | Leads | CPL |
|----|-------------|--------|-----|-------|-----|

### Flags
- [any ad sets with frequency > 3 — creative fatigue risk]
- [any ad sets with CPL > 2x average — consider pausing]
- [any ads with CTR < 0.5% — underperforming]
```

### Optimize

When asked to optimize or when flagging issues:

1. **Kill underperformers:** Pause any ad with CPL > 2x the campaign average after 1000+ impressions
2. **Shift budget:** Move budget from worst ad set to best ad set
3. **Refresh creative:** If any ad set frequency > 3, generate new ad copy and swap in
4. **Expand winners:** If an ad set has CPL below target and budget headroom, increase by 20%

Always explain what you're doing and why before making changes.

### A/B Test

For each ad set, maintain 2-3 ad variations. After 500+ impressions each:

1. Compare CTR and CPL across variations
2. Pause the worst performer
3. Generate a new variation to replace it (use ad-copy skill)
4. Keep the cycle going: always have at least 2 live ads per ad set

### Audience Research

When exploring new audiences:

1. `mcp_meta_ads_search_interests` to find targeting options
2. `mcp_meta_ads_get_interest_suggestions` for related interests
3. `mcp_meta_ads_search_behaviors` for behavior targeting
4. `mcp_meta_ads_search_geo_locations` for geo targeting

Present findings as a targeting plan with estimated audience size.

## Budget Guidelines

| Phase | Daily Budget | Duration | Goal |
|-------|-------------|----------|------|
| Test | $20-50/day total | 1-2 weeks | Find winning ad set + creative |
| Scale | $50-150/day total | Ongoing | Drive leads at target CPL |
| Push | $150-300/day total | When deal needs volume | Maximize qualified leads |

## Key Metrics to Track

- **Cost per Lead (CPL)** — the number that matters most
- **CTR** — above 1% is good for real estate, above 2% is great
- **Frequency** — above 3 means the audience is seeing the ad too many times
- **Lead quality** — cross-reference with lead scorer. Cheap leads that never qualify are worthless.
