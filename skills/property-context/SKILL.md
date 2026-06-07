---
name: property-context
description: Load and format the canonical property context from data/property.json for use by every lead-facing skill. Use whenever you are about to write ad copy, a follow-up, nurture content, a landing-page section, or anything else that references the property. Prevents hallucinated facts and enforces anti-slop rules.
user-invokable: false
---

# Property Context

You are the single source of truth for property facts. Every skill that touches a lead or prospect invokes you first, then uses your output as the reference block.

## Process

1. Read `data/property.json`.
2. If any top-level field still contains the literal string `"UPDATE"`, stop and return:
   ```
   BLOCKED: data/property.json has placeholder "UPDATE" values. Populate real content before generating lead-facing output.
   ```
   Do not attempt to synthesize or guess any facts.
3. Otherwise, emit the Context Block below, filled in from the JSON.

## Context Block (emit verbatim, with values substituted)

```
# PROPERTY CONTEXT — reference these facts exactly. Do not invent.

Project: {project_name}
Location: {location.city}, {location.region}, {location.country}
Location description: {location.description}

Inventory:
  - Lots: {inventory.lots.total} total, {inventory.lots.available} available, size {inventory.lots.size_range}, price {inventory.lots.price_range}
  - Complex units: {inventory.complex_units.total} total, {inventory.complex_units.available} available, types {inventory.complex_units.types}, price {inventory.complex_units.price_range}

Deal structure: {deal_structure.type} — {deal_structure.details}

Key selling points:
{key_selling_points as bullets}

Target audience profiles:
{target_audiences as list — each shows id, hook, budget_range}

Amenities: {amenities joined}
Timeline: phase 1 {timeline.phase_1}, completion {timeline.completion}

Media available: {media fields that are non-null}

Sales contact: {contact.sales_name} — {contact.sales_email} — {contact.sales_phone} — WhatsApp {contact.sales_whatsapp}
```

## Writing rules that travel with this context

Whenever you emit the context block, append these rules so the consuming skill honors them:

```
# WRITING RULES (from CLAUDE.md — do not violate)
- No "AI slop": never use "nestled in", "boasts", "stunning", "hidden gem", "paradise awaits", "I hope this finds you well", em-dashes, or any filler real-estate adjectives.
- First-person, concrete, specific. Reference an actual number, lot, amenity, or timeline detail.
- One CTA per lead-facing message.
- WhatsApp for time-sensitive contact (score >= 70). Email for artifacts (brochure, site plan, payment schedule).
- Convert any Meta Ads API budget values from cents to dollars for display.
- If a fact is not in the context block above, do not assert it. Either omit or ask the sales contact.
```

## Output contract

Your only output is the filled Context Block + Writing Rules block, separated by a blank line. No preamble, no commentary. The caller pastes this at the top of their own prompt.

## When to re-read

Re-read `data/property.json` at the start of every session. Do not cache between runs — the file is the source of truth and may have been updated.
