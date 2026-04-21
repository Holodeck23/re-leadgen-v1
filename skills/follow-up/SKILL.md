---
name: re-follow-up
description: Draft personalized follow-up messages for qualified real estate leads
---

# Real Estate Follow-Up Drafter

Draft personalized follow-up emails and WhatsApp messages for leads based on their
score, interest, and the notes from the lead qualifier.

## When to Use

- After leads have been scored by the lead-qualifier skill
- When follow_up_date is today or overdue
- When a lead replies and needs a response

## Nurture Sequences

Read `data/nurture-sequences.json` before drafting. It defines the drip cadence
for each lead tier (hot, warm, cool). Match the message type and timing to where
the lead is in their sequence. Check the lead's status and last contact date to
determine which step they're on.

## Property Reference

Read `data/property.json` for listing details. Never make up facts about the
property. If the property data is incomplete (fields say "UPDATE"), flag it
and skip that detail rather than inventing something.

## Message Types

### 1. Initial Outreach (status: qualified, no prior contact)

**Email** — Send the property package. Personalize based on their interest type.

Template structure:
- Subject line: specific to their interest, not generic
- Opening: acknowledge what they asked about (from form message field)
- Body: 2-3 key facts about the property that match their interest
- Attachment mention: "I've attached the full property package with lot maps, pricing, and the development timeline."
- CTA: suggest a specific next step (call, WhatsApp, reply)
- Sign-off: casual professional, not corporate

**WhatsApp** — Shorter version. 3-4 sentences max. Link to property package instead of attachment.

### 2. Nurture (status: nurture, score 3-4)

Lighter touch. Share one interesting update or fact about the development.
No hard sell. Keep the door open.

Examples:
- "[N] lots sold this month — inventory moving."
- "New drone footage of the development just came in. Want to see it?"
- "Quick update: infrastructure work on Phase 1 starts [date]."

### 3. Hot Lead Follow-Up (score 8-10, no response to initial outreach)

More direct. Acknowledge they're busy. Offer a specific time for a quick call.
Make it easy to say yes.

### 4. Re-Engagement (status: cold or no response after 2+ follow-ups)

One final touch. Low pressure. "No worries if the timing isn't right —
just wanted to make sure you had everything you needed."

## Writing Rules

1. **First person, casual professional.** Not "Dear valued prospect." Just talk like a person.
2. **No AI slop.** No "I hope this email finds you well." No "I wanted to reach out." No "don't hesitate to."
3. **Reference something specific** from their form submission. Budget, interest type, message — anything that shows this isn't a blast.
4. **Keep it short.** Emails: 5-8 sentences. WhatsApp: 3-4 sentences.
5. **One CTA per message.** Don't ask them to call AND email AND visit a website.
6. **Match urgency to score.** Hot leads get "when works for a quick call?" Cool leads get "no rush."

## Output Format

```
## [Lead Name] — [Message Type]

**Channel:** Email / WhatsApp
**Subject:** [for email only]

---

[Message body]

---

**Send by:** [date]
**Next step if no response:** [what to do and when]
```

## Batch Mode

When processing multiple leads, group by message type and generate all at once.
Output a summary table at the end:

| Lead | Score | Channel | Subject/Hook | Send By |
|------|-------|---------|-------------|---------|
