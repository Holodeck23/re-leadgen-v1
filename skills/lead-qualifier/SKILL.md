---
name: lead-qualifier
description: Score incoming real-estate leads on a 0-100 scale using BANT + behavioral + property-fit signals loaded from data/scoring-model.json. Produce an explanation, a tier, and a recommended channel + SLA. Use when processing new leads from the sheet or a webhook payload.
user-invokable: true
---

# Lead Qualifier (BANT + Behavioral + Property-Fit)

You score one or more leads against the rubric in `data/scoring-model.json`. Every score must be reproducible from the rubric — if you cannot explain a point award from the JSON, do not award it.

## Process

1. **Load rubric.** Read `data/scoring-model.json`. If the file is missing or malformed, STOP and return `ERROR: scoring model unavailable`.
2. **Load property context.** Invoke `property-context` skill. The lead's `budget` and `interest` fields are compared against `inventory.*.price_range` and `target_audiences` from property.json. If property-context returns BLOCKED, STOP.
3. **Parse lead.** Required sheet columns: `name, email, phone, interest, budget, timeline, message, source`. Optional: `return_visitor`, `event_id`. Preserve raw values; do not mutate the lead record.
4. **Extract signals.** For each feature category in `scoring-model.json.features`, evaluate which weighted signals apply:
   - **budget_capacity**: parse budget range, compare to listing range. Scan `message` for "cash", "pre-approved", "pre-approval", "financing approved" (case-insensitive) → `pre_approved_or_cash`.
   - **authority**: scan `message` for "I", "my wife/husband/partner", "need my ... approval".
   - **need_specificity**: check `interest` field + scan `message` for specific lot numbers, unit types, phase names.
   - **timeline**: map `timeline` field to bucket.
   - **behavioral**: presence of `phone`, whatsapp (if phone starts +country and message mentions WhatsApp or channel=whatsapp), message length, specific questions (does message contain "?"), `return_visitor=true`, engagement-with-first-followup (from sheet notes if prior contact recorded).
   - **source_quality**: parse `source` field. UTM `utm_source=organic` or `referral` → bump. `utm_medium=cpc` + `utm_campaign` with "retargeting" → retargeting. Otherwise check `utm_campaign` against known lookalike vs prospecting naming conventions.
   - **risk_flags**: check for missing phone+message, disposable-email domains (mailinator, tempmail, 10minute, yopmail, guerrillamail), duplicate leads within 30 days.
5. **Sum to score.** Apply weights literally. Clamp to `[0, 100]`.
6. **Assign tier.** Compare score to `tiers.hot.min`, `tiers.nurture.min`, else `long_cycle`.
7. **Match segment.** Compare lead's message + interest against each `audience_segments.segments[].signals` array (case-insensitive substring match). Assign the first matching segment; default `generic`.
8. **Produce the output record** (see below).

## Output (one record per lead)

```json
{
  "lead_id": "<row or email-phone hash>",
  "score": 78,
  "tier": "hot",
  "segment": "investor",
  "channel_primary": "whatsapp",
  "channel_artifacts": "email",
  "sla_hours": 2,
  "signals_awarded": [
    { "feature": "budget_capacity", "signal": "budget_in_range", "points": 20 },
    { "feature": "timeline", "signal": "ready_now_to_30_days", "points": 25 },
    { "feature": "need_specificity", "signal": "specific_lot_or_unit_named", "points": 15 },
    { "feature": "behavioral", "signal": "phone_provided", "points": 5 },
    { "feature": "behavioral", "signal": "asked_specific_questions", "points": 6 },
    { "feature": "source_quality", "signal": "organic_social", "points": 10 }
  ],
  "risk_flags": [],
  "notes": "Hot investor lead: budget fits lot range, ready-now timeline, asked about Phase 1 infra and ROI. Organic IG source. Contact via WhatsApp within 2h."
}
```

The `notes` field is what will be written to the Google Sheet `notes` column. It must:
- Start with the tier + segment.
- Cite 2–3 specific awarded signals (not all of them).
- End with the recommended next action and SLA.
- Be ≤ 280 chars (fits one-line sheet cell).
- Honor anti-slop rules from CLAUDE.md: no "exciting prospect", no "great fit", no em-dashes, no filler adjectives.

## Batch mode

If given multiple leads, return `{"scored": [...], "hot_count": N, "nurture_count": N, "long_cycle_count": N}` and sort the `scored` array by score descending. If `hot_count > 0`, also emit the banner:
```
ALERT: {hot_count} hot leads need contact within 2 hours.
```

## Guardrails

- **Never invent fields.** If a sheet column is missing, score what is present and note the missing signal in `notes`.
- **Do not mutate the rubric.** If the rubric feels wrong for a lead, say so in the returned analysis but do not silently deviate.
- **Explain in notes.** `scoring-model.json.explain_in_notes=true` is contractual.
- **Duplicates.** If you detect a duplicate lead (same phone or email in sheet within 30 days with status != "closed"), apply the `duplicate_within_30_days` penalty and set `notes` to reference the prior row.

## Files this skill reads

- `data/scoring-model.json` (rubric)
- `data/property.json` (via `property-context`)
- Sheet rows passed in by caller (typically via `scripts/sheet-ops.py new`)
