---
name: unicorn-promoter
description: Apply Larry Kim's unicorn methodology to organic Meta posts. Rank posts by hook-rate + CTR percentile against the account's 30-day baseline, surface the top 10% outliers, and propose a $50 audition budget to promote only those. Use when planning new creative or during the daily reflective-ops loop.
user-invokable: true
---

# Unicorn Promoter (Larry Kim methodology)

The premise: 95% of organic social content performs at baseline. The top 2–3% ("unicorns") get 3–10× the engagement of the rest. Promoting a unicorn as a paid ad inherits its organic relevance — CPMs drop, CTR stays high, CPL compresses. Promoting a non-unicorn burns money.

You do not create creative. You rank existing organic posts and decide which deserve a paid audition.

## Process

1. **Pull organic post metrics.** Via Meta Ads MCP (`mcp__meta-ads__*`), fetch the last 30 days of Instagram + Facebook organic posts from the advertiser's connected page / IG account. Required metrics per post:
   - Impressions (organic)
   - Reach (organic)
   - 3-second video views (for reels/videos)
   - Link clicks / profile visits
   - Saves + Shares
   - Reactions + Comments
   - Post duration (for videos)
   - Format (image, carousel, reel, video, story)

2. **Compute derived metrics per post.**
   - `hook_rate_3s = 3s_views / impressions` (video only)
   - `engagement_rate = (reactions + comments + saves + shares) / reach`
   - `ctr = link_clicks / impressions`
   - `hold_rate = avg_watch_time / duration` (video only)

3. **Compute 30-day account baselines** (median, not mean — robust to the unicorn itself skewing mean).
   - Baselines per metric AND per format (e.g. reel hook_rate_3s median vs image engagement_rate median).

4. **Score each post.**
   - For each metric with a baseline, compute `multiplier = post_metric / format_baseline`.
   - Primary composite score: `0.4 * hook_rate_multiplier + 0.3 * ctr_multiplier + 0.3 * engagement_multiplier` (drop the hook_rate term for non-video).
   - Outlier threshold: `composite_score >= 3.0` (≥3× baseline) OR `>=90th percentile`.

5. **Filter for on-brand content.**
   - Load `property-context`. Reject posts that do not reference the project, the location, or a relevant theme (drone footage, lot map, construction, testimonials, market context). A post about the owner's vacation is not a candidate even if it's an engagement unicorn.
   - Reject posts that violate the anti-slop rules from CLAUDE.md — we cannot promote copy we would reject.

6. **Rank and produce the candidate list.**

```json
{
  "window_days": 30,
  "baseline_sample_size": 42,
  "candidates": [
    {
      "post_id": "...",
      "permalink": "...",
      "format": "reel",
      "composite_score": 4.2,
      "hook_rate_3s": 0.38,
      "hook_rate_baseline": 0.12,
      "ctr": 0.022,
      "engagement_rate": 0.087,
      "on_brand": true,
      "segment_fit": "investor",
      "proposed_action": {
        "type": "paid_audition",
        "budget_usd": 50,
        "duration_days": 3,
        "audience": "lookalike_1pct_of_hot_leads",
        "placements": ["instagram_reels", "facebook_feed"],
        "objective": "OUTCOME_LEADS",
        "requires_approval": true
      },
      "rationale": "Reel: 3x hook rate vs IG baseline, lands specifically on Phase 1 infra progress, strong fit for investor segment."
    }
  ],
  "rejected_unicorns": [
    { "post_id": "...", "reason": "off-brand (owner vacation post)" },
    { "post_id": "...", "reason": "violates anti-slop: uses 'nestled in'" }
  ],
  "no_unicorns_found": false
}
```

7. **Never promote non-unicorns.** If no post clears the threshold, return `no_unicorns_found: true` and propose a content test plan (what hooks/angles to try next 2 weeks) instead of promoting anything. Spending on non-unicorns is the main failure mode this skill prevents.

## Approval gate

All `paid_audition` proposals are `requires_approval: true` by default. The reflective-ops loop shows them to the human in the morning briefing. Reason: promoting the wrong post because it happened to spike on a meme is a classic failure — we keep a human in the loop for the promotion decision.

## Audience seed

When proposing `lookalike_1pct_of_hot_leads`, the seed is a custom audience built from sheet rows where `score >= 70`. If the sheet has fewer than 100 hot leads yet, fall back to `broad` audience (Advantage+ audience) and note the small-seed caveat.

## Guardrails

- **Minimum sample size.** Need at least 15 organic posts in the window to compute stable medians. If fewer, return `BLOCKED: not enough organic content for unicorn detection. Recommended: post 15+ distinct organic assets over the next 4 weeks.`
- **Cold-start mode.** If this is the first run and there is no 30-day baseline: score posts relative to each other (top 3 per format) but tag each proposal `cold_start: true` with confidence 0.5 max.
- **Cadence.** Run weekly, not daily — organic metrics need 5–7 days to settle.

## Files this skill reads / writes

- Meta Ads MCP (read-only on organic metrics)
- `data/property.json` (via `property-context`)
- `data/kill-scale-rules.json` (for budget cap awareness)
- Sheet rows for lookalike seed
- Appends candidate lists to `data/ad-history.jsonl` so reflective-ops can see them in context next run
