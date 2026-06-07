---
name: nurture-orchestrator
description: Advance leads through milestone-triggered nurture sequences (defined in data/nurture-sequences.json). Runs each lead against its current tier's sequence, checks which step should fire now (trigger met OR max_wait elapsed), and drafts the corresponding message via the follow-up skill. Use in the daily reflective-ops loop and when a new milestone event is published.
user-invokable: true
---

# Nurture Orchestrator

You advance the next correct step for every lead not in a terminal state. Unlike a calendar drip, you fire on *new information* — a milestone, a reply, a score change — and use the calendar only as a fallback.

## Process

1. **Load data.**
   - `data/nurture-sequences.json` → sequences + milestone types
   - `data/scoring-model.json` → tier → sequence mapping (`hot` → `sequences.hot`, `nurture` → `sequences.nurture`, `long_cycle` → `sequences.long_cycle`)
   - Sheet rows for leads with `status` in `{new, contacted, nurturing, reengage}` — exclude `closed`, `lost`, `duplicate`.
   - Recent milestones: the caller passes a list of events that occurred since the last run (or read from `data/ad-history.jsonl` if ops-logged there).

2. **For each eligible lead, determine current step.**
   - Parse `notes` field or a `sequence_state` column (if present) to identify the last completed step `id`.
   - If none, current step = first step of the lead's tier sequence.

3. **Determine if the current step should fire now.**
   - Fire if ANY of:
     - A new milestone event matches one of the step's `triggers[].milestone` conditions.
     - Lead replied since last step was scheduled → fire the first post-reply step (usually a call or artifact).
     - `max_wait_hours` or `max_wait_days` has elapsed since the previous step's fire time (calendar fallback).
   - Otherwise, hold and log the next `revisit_at`.

4. **Draft the message.** Invoke the `follow-up` skill for the step's channel, tier, and action. Pass the lead record + the milestone event (if any) so follow-up can reference it specifically.

5. **Produce the action queue.** Do not send messages yourself. Emit a structured queue for the human/operator to approve or the scheduler to dispatch:

```json
[
  {
    "lead_id": "...",
    "lead_tier": "nurture",
    "segment": "investor",
    "sequence_step_id": "nurture_02_milestone_update",
    "channel": "email",
    "trigger": { "type": "milestone", "condition": "new_drone_footage_published" },
    "draft": { "subject": "...", "body": "..." },
    "send_at": "next_business_hour",
    "revisit_if_no_reply_at": "2026-05-05T10:00:00Z"
  }
]
```

6. **Downgrade or upgrade tier if warranted.**
   - If a lead reached the terminal step of its sequence with no reply → downgrade tier (hot → nurture → long_cycle) and reset sequence_state to first step of new tier.
   - If a long_cycle lead replies with hot signals (timeline, pre-approval, specific unit) → upgrade: invoke `lead-qualifier` again on their updated info.

## Milestone sources

You do not discover milestones yourself. The caller provides them. Sources that should call you:
- `reflective-ops` daily loop (passes recently-logged milestones from `data/ad-history.jsonl` and any updates the user noted)
- A manual invocation from the user: "we published new drone footage today, advance nurture"
- Webhook from `form-handler.gs` for `on_reply` events (future)

## Guardrails

- **One active step per lead.** Do not fire two steps simultaneously — if a milestone trigger fires, skip the calendar step and advance.
- **Quiet hours.** Do not set `send_at` inside 10pm–7am local to the lead. Shift to next business hour.
- **Rate-limit.** At most 1 message per lead per 48h unless the lead replied.
- **Hot tier exception.** Hot leads bypass rate-limit within first 24h (time-to-contact matters).
- **Anti-slop.** All drafts route through `follow-up` which enforces the rules.

## Files this skill reads

- `data/nurture-sequences.json`
- `data/scoring-model.json` (for tier thresholds and segment lookups)
- `data/property.json` (via `property-context`, transitively through `follow-up`)
- Sheet rows via `scripts/sheet-ops.py all`
- `data/ad-history.jsonl` (optional — for milestone context)
