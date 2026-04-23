---
name: re-daily-ops
description: Morning briefing — new leads, ad performance, follow-ups due, pipeline summary
---

# Daily Operations Briefing

Run this every morning (or whenever you sit down to work on the deal).
Pulls together everything that happened since the last check.

## When to Use

- Start of each work session
- When asked "what's going on" or "give me the rundown" or "morning briefing"

## Process

### 1. New Leads

Check for leads with status "new":
```bash
python scripts/sheet-ops.py new
```

If there are new leads:
- Score them using the `lead-qualifier` skill
- Flag any hot leads (8+) at the top
- Update the sheet

If no new leads, say so. Don't pad it.

### 2. Ad Performance (last 24h)

If Meta Ads MCP is connected:
- Pull insights for active campaigns (last 1 day)
- Report: spend, leads, CPL, CTR
- Flag anything that needs attention (high frequency, tanking CTR, budget maxed out)

If not connected, skip this section and note that MCP isn't set up yet.

### 3. Follow-Ups Due

Check for leads with follow-up dates today or overdue:
```bash
python scripts/sheet-ops.py due
```

If there are leads due:
- List them with their score and last status
- Draft follow-up messages using the `follow-up` skill

### 4. Pipeline Summary

Pull all leads and summarize:

```
## Pipeline — [date]

| Status | Count |
|--------|-------|
| New (unscored) | N |
| Hot (8-10) | N |
| Warm (5-7) | N |
| Cool (3-4) | N |
| Cold (1-2) | N |
| Contacted | N |
| Qualified | N |
| Closed | N |

**Total leads:** N
**Conversion rate:** N% (qualified / total)
**This week:** N new leads, $X ad spend, $X CPL
```

### 5. Recommendations

Based on everything above, give 1-3 specific actions:
- "CPL is climbing — refresh ad creative today"
- "3 hot leads haven't been contacted — call them"
- "No new leads in 48 hours — check if the landing page form is working"
- "Budget underspent — ads may have been paused, check campaign status"

Keep it short. Lead with what matters.

## Output Format

```
# Daily Briefing — [date]

**TL;DR:** [one sentence: the most important thing right now]

## New Leads
[scored leads or "none"]

## Ads
[performance summary or "MCP not connected"]

## Follow-Ups Due
[list with drafted messages or "none due today"]

## Pipeline
[summary table]

## Do This Today
1. [action]
2. [action]
3. [action]
```
