---
name: follow-up
description: Draft personalized follow-up messages (WhatsApp and email) for qualified real-estate leads, channel-selected by score tier and audience segment. Use after lead-qualifier has scored a lead, or when the user asks for follow-up copy for a specific row.
user-invokable: true
---

# Follow-Up Drafter (WhatsApp-first, multivariate)

You draft outreach messages for one lead at a time. Always tailor to the segment, the tier's channel preference, and the specific facts the lead shared in the form or last conversation.

## Process

1. **Load context.** Invoke `property-context` skill. If BLOCKED, STOP.
2. **Load segment pitches.** Read `data/scoring-model.json` → `audience_segments.segments[]`. Find the segment matching the lead's assigned `segment` (from lead-qualifier output) and use its `pitch` as the content spine.
3. **Pick channel.** Use `tiers.{tier}.channel`:
   - `hot` (score ≥70): WhatsApp first, then phone call, then email artifact.
   - `nurture` (40–69): Email first (artifact-bearing), WhatsApp follow-up if no reply in 48h.
   - `long_cycle` (<40): Email drip only.
4. **Check reply history.** If the lead has prior `notes` indicating earlier outreach, produce the next message in the sequence (re-engagement, not first-contact).
5. **Draft per-channel versions.** For the chosen primary channel, produce 2 variants (A/B). For the secondary channel (when applicable), produce 1.

## Channel rules

### WhatsApp (Shadowban Protection)
**To avoid being flagged as spam by Meta/WhatsApp:**
- **Extreme Personalization**: The first message must be 100% unique. Reference a specific fact from their message or interest field. Never use a template for the first touch.
- **Reply-Bait**: Always end with a low-friction question to encourage a reply. A lead replying "whitelists" your number in WhatsApp's spam filters. 
  - *Good*: "Want me to send the Phase 1 lot map via WhatsApp?"
  - *Bad*: "Let me know if you have questions."
- **No Links on First Touch**: Unless specifically asked for a link, do not include URLs in the first WhatsApp message. 
- ≤3 sentences. First sentence names them and one specific thing they said or asked about.
- No greeting boilerplate ("Hi, hope you're doing well"). Open with the content.
- No emojis unless the lead used one first.

### Email
- 5–8 sentences, plain text (no HTML unless explicitly asked).
- Subject line: specific, ≤55 chars. Reference project name + a concrete number or the lead's stated interest. Never use "Following up", "Touching base", "Quick question".
- Body opens with a direct acknowledgment of what they asked + one proof point from `property-context`. Attach or link one artifact (brochure, lot map, video).
- One CTA. Prefer "Reply with the lot number that caught your eye" over generic "let me know".

## Segment content spines (use literally, adapt wording)

- **investor**: ROI pitch + appreciation (Phase-2 price bump, comparable-sales lift) + rental/build-to-sell math if available.
- **homebuyer**: Lifestyle + lot size + schools/community + access (road, airport, hospital).
- **retiree**: Community + services + healthcare access + climate + security.
- **expat**: Residency/visa process + title clarity + foreign-ownership rules + tax.
- **generic**: Lead with the single strongest property proof point, then ask the qualifying question that will route them to a segment.

## Anti-slop (from CLAUDE.md — non-negotiable)

Do not use: "nestled in", "boasts", "stunning", "hidden gem", "paradise awaits", "don't miss out", "I hope this finds you well", "just checking in", "touching base", em-dashes, three-dot ellipses, any filler adjective.

Every draft must reference at least one of: a specific lot or unit, a specific price or price range, a specific timeline date, a specific amenity name, or something the lead said verbatim.

## Output shape

```json
{
  "lead_id": "...",
  "tier": "hot",
  "segment": "investor",
  "channel_primary": "whatsapp",
  "channel_secondary": "email",
  "drafts": {
    "whatsapp": [
      { "variant": "A", "text": "..." },
      { "variant": "B", "text": "..." }
    ],
    "email": [
      { "variant": "A", "subject": "...", "body": "..." }
    ]
  },
  "send_at": "immediate" | "next_business_hour" | "YYYY-MM-DDTHH:MM",
  "expected_next_action": "If reply within 24h, book call. If no reply in 48h, send email variant A."
}
```

## Guardrails

- Never fabricate property facts. Every claim comes from `property-context`.
- Never send "Hi {name}, thanks for your interest" — that's the exact pattern we're replacing.
- If the lead's message contained a question, answer it in the first sentence.
- If you cannot personalize past {name, interest}, flag it in `expected_next_action` and keep the draft ≤2 sentences.

## Files this skill reads

- `data/property.json` (via `property-context`)
- `data/scoring-model.json` (for segment pitches)
- The lead record passed in by caller (with score, tier, segment from `lead-qualifier`)
- Optional: `data/nurture-sequences.json` if the lead is in an ongoing sequence
