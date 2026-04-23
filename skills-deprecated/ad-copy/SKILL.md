---
name: re-ad-copy
description: Generate Facebook and Instagram ad copy variations for real estate listings
---

# Real Estate Ad Copy Generator

Generate high-converting Facebook and Instagram ad copy for real estate listings.
Produces multiple variations optimized for different audiences and placements.

## When to Use

- Launching a new FB/IG campaign for property listings
- A/B testing ad creative
- Refreshing stale ads (creative fatigue)
- Targeting different buyer segments

## Inputs Required

Before generating, gather:
1. **Property details** — location, lot count, price range, key features
2. **Target audience** — investors, first-time buyers, retirees, expats, etc.
3. **Campaign objective** — leads, traffic, awareness
4. **Any existing brand voice or constraints**

If these aren't provided, ask before generating.

## Output Format

For each variation, produce:

```
## Ad Variation [N] — [Audience Segment]

**Placement:** [Feed / Stories / Reels]
**Headline:** (40 chars max)
**Primary Text:** (125 chars for feed, 72 for stories)
**Description:** (30 chars max)
**CTA Button:** [Learn More / Sign Up / Get Quote / Contact Us]

**Full Primary Text (extended):**
[The longer version for feed placements, up to 3-4 sentences]
```

## Generation Rules

1. **Lead with the hook, not the feature.** "Your own lot from $X" beats "89 lots available."
2. **One idea per ad.** Don't cram investment + lifestyle + location into one ad.
3. **Use numbers.** Price, lot count, distance to amenities, ROI percentages.
4. **Match tone to audience:**
   - Investors: ROI, rental yield, appreciation, portfolio
   - Homebuyers: lifestyle, community, space, family
   - Retirees: peace, nature, value, turnkey
   - Expats: affordability, weather, ease of purchase
5. **No AI slop.** No "nestled in," "boasts," "stunning," "dream home awaits." Write like a person.
6. **Include urgency only if real.** "Limited lots" is fine if true. No fake countdown timers.
7. **Always include a clear CTA.** What should they do next?

## Variations to Generate

Produce **6 variations** per run:
- 2x Feed ads (different audiences)
- 2x Stories/Reels ads (shorter, punchier)
- 1x Carousel concept (3-5 cards outlined)
- 1x Retargeting ad (for people who visited the landing page)

## Meta Ads MCP Integration

If the Meta Ads MCP server is connected, you can:
- Create the ads directly via `mcp_meta_ads_create_ad_creative`
- Upload images via `mcp_meta_ads_upload_ad_image`
- Search for targeting interests via `mcp_meta_ads_search_interests`
- Check performance of running ads via `mcp_meta_ads_get_insights`

## Example

**Property:** 89 development lots + complex units, Honduras
**Audience:** US-based real estate investors
**Placement:** Facebook Feed

**Headline:** Own Land for Under $100K
**Primary Text:** 89 lots. One development. Profit share structure with the owner. This isn't a timeshare pitch — it's raw land at pre-development prices.
**CTA:** Get the Details
