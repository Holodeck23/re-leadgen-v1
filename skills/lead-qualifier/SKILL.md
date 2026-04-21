---
name: re-lead-qualifier
description: Score and qualify real estate leads from the Google Sheet
---

# Real Estate Lead Qualifier

Score incoming leads from the Google Sheet and flag hot prospects for immediate follow-up.

## When to Use

- New leads have come in (status = "new" in the sheet)
- Periodic review of all leads
- Before drafting follow-up messages

## Lead Scoring Criteria

Score each lead 1-10 based on these dimensions:

### High-Signal Indicators (weighted heavily)
| Signal | Points |
|--------|--------|
| Budget matches or exceeds listing price range | +3 |
| Timeline is "Ready Now" or "1-3 Months" | +2 |
| Interest is "Multiple Properties" or "Investment" | +2 |
| Phone number provided | +1 |
| Message field filled out with specific questions | +1 |

### Medium-Signal Indicators
| Signal | Points |
|--------|--------|
| Timeline is "3-6 Months" | +1 |
| Interest is "lot" or "unit" (specific, not browsing) | +1 |

### Low-Signal / Deductions
| Signal | Points |
|--------|--------|
| No phone number, no message | -1 |
| Budget "Under $100K" for premium lots | 0 (neutral, could be lot buyer) |
| Timeline "Just Exploring" | -1 |

### Score Interpretation
| Score | Label | Action |
|-------|-------|--------|
| 8-10 | Hot | Contact within 2 hours. Phone call preferred. |
| 5-7 | Warm | Email within 24 hours with property package. |
| 3-4 | Cool | Add to nurture sequence. Follow up in 1 week. |
| 1-2 | Cold | Add to newsletter. No active follow-up. |

## Process

1. Read all leads with status "new" from the sheet
2. Score each lead using the criteria above
3. Generate a brief note for each lead (1-2 sentences: why this score, what to mention in follow-up)
4. Set follow_up_date based on score tier
5. Update the sheet: fill in score, status (qualified/nurture/cold), notes, follow_up_date

## Output Format

For each scored lead, output:

```
[Name] — Score: [N]/10 ([Hot/Warm/Cool/Cold])
  Budget: [budget] | Timeline: [timeline] | Interest: [interest]
  Note: [why this score, what to mention in follow-up]
  Action: [specific next step]
  Follow-up by: [date]
```

Then provide a summary:
```
--- Lead Batch Summary ---
Total new leads: [N]
Hot (8-10): [N] — contact ASAP
Warm (5-7): [N] — email today
Cool (3-4): [N] — nurture sequence
Cold (1-2): [N] — newsletter only
```

## Google Sheets Integration

Use the `scripts/sheet-ops.py` helper to read/write the sheet, or work with the sheet data
if provided as CSV/JSON input.

The sheet columns are:
timestamp, name, email, phone, interest, budget, timeline, message, source, score, status, notes, follow_up_date
