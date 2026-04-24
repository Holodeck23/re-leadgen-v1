# Project Instructions

You are operating a real-estate lead-generation system for a live deal: 89 development lots + a residential complex, profit-share structure with the property owner.

Read `docs/walkthrough.md` once for the full tour. Read `docs/runbook.md` before acting on any escalation. This file is the rules you operate under.

## Your role

You are the marketing and lead-operations layer. You generate ads, manage campaigns, score incoming leads, draft follow-ups, and run the daily reflective loop. The human handles sales calls and closing.

## MCP servers

Meta Ads is connected via Pipeboard (remote MCP, configured in `.mcp.json`). Use it for every Meta action — never hit the Graph API directly from Claude.

Authenticate via Pipeboard token. If auth fails, tell the user to refresh at https://pipeboard.co/api-tokens.

## Single source of truth

- **`data/property.json`** — every lead-facing fact (prices, inventory, location, amenities, media, contact). Never invent. Blocked from go-live until all `UPDATE` placeholders are replaced.
- **`data/kill-scale-rules.json`** — pause/scale/refresh thresholds, auto-approval list, statistical guardrails. Read by `reflective-ops`, `paid-ads`, `ads-meta`. Edit deliberately.
- **`data/scoring-model.json`** — BANT + behavioural + property-fit weights. Read by `lead-qualifier`. Tune weekly. Includes `initial_phase` config (Strategy B): first-submission leads get tier overrides based on intent + phone, while full-rubric score is computed for the quality gate.
- **`data/creative-library.jsonl`** — pre-approved ad creative variants (one JSON object per line). Read by `reflective-ops` for `refresh_creative` and `launch_variant`. Each line: `{id, format, segment, headline, primary_text, image_ref, status}`. Empty until populated via `ad-creative` or `campaign-launch` skill.
- **`data/launch-config.json`** — created by `campaign-launch` skill at first launch. Records campaigns, ad sets, audience snapshots, and learning-phase guardrails. Read by `reflective-ops` to enforce learning-phase restrictions (14 days / 50 Lead events). Do not edit during learning phase unless you understand the consequences.
- **`data/nurture-sequences.json`** — tier-matched sequences, milestone-triggered. Read by `nurture-orchestrator`.
- **`data/ad-history.jsonl`** — append-only decision log. Read by `reflective-ops` to recover context each run.

Always load `data/property.json` via the `property-context` skill — it produces the canonical context block plus anti-slop rules. Do not hardcode property facts.

## Skills

Read the full SKILL.md before using any skill. Don't paraphrase from memory.

### Foundation
- `skills/property-context/` — loads `data/property.json` and emits the context block + anti-slop rules. Every lead-facing skill invokes this first.

### Daily operations (the brain)
- `skills/reflective-ops/` — the daily analyze → iterate → execute loop. Driven by `agents/reflective-operator.md` via `scripts/loop-runner.sh`. Modes: `full`, `hot_sweep`, `dry_run`, `emergency_brake`.

### Lead handling
- `skills/lead-qualifier/` — BANT + behavioural + property-fit scoring per `data/scoring-model.json`. Returns `{score, tier, segment, signals_awarded, notes, sla_hours}`.
- `skills/follow-up/` — WhatsApp-first (≤3 sentences) for hot leads; email (5–8 sentences) for artefacts. Segment-aware copy spines. Anti-slop enforced.
- `skills/nurture-orchestrator/` — advances leads through milestone-triggered sequences from `data/nurture-sequences.json`. Respects 22:00–07:00 quiet hours.

### Campaign creation (zero to live)
- `skills/campaign-launch/` — end-to-end campaign creation for users with zero ads experience. 9-step sequence: validate → Pixel check → audience research → creative → structure → pre-launch checklist → create via API → write launch config → go live. All with user approval gates.
- `skills/audience-research/` — builds Meta ad targeting from property data. Produces segment-specific interest stacks, location targeting, retargeting audiences, and exclusions. Housing Special Ad Category compliant. Called by `campaign-launch` step 3.

### Ads (ongoing management)
- `skills/ad-creative/` — generate or iterate-from-performance. Produces 6 Meta variants (2 Feed, 2 Reels, 1 Carousel, 1 Retargeting). Enhanced with psychological hook categories (curiosity gap, social proof, specificity, loss aversion, identity, pattern interrupt).
- `skills/paid-ads/` — campaign lifecycle (launch, pause, scale, refresh) under `kill-scale-rules.json` thresholds. Meta-only. `OUTCOME_LEADS` objective. Daily-budget cap is a hard stop.
- `skills/ads-meta/` — creative fatigue, audience overlap, Pixel/CAPI health audit. Paper trail only; never auto-pauses — `reflective-ops` owns execution.
- `skills/ads-generate/` — image generation; prefers real photography from `property.json` over AI.
- `skills/unicorn-promoter/` — Larry-Kim unicorn methodology. Ranks organic posts by hook-rate + CTR percentile; flags outliers for $50 auditions. Requires approval.

### Measurement + experiments
- `skills/analytics-tracking/` — Meta Pixel + CAPI instrumentation, UTM capture, `quality-by-adset` query definition.
- `skills/ab-test-setup/` — hook × angle × offer matrix. Hypothesis format (IF/THEN/BECAUSE/REVISIT) is mandatory. Minimums: 1000 impressions / 10 leads / $50 spend.
- `skills/page-cro/` — landing-page optimisation.
- `skills/form-cro/` — form optimisation (locked at 3 fields: name, phone, interest).

## Agents

- `agents/campaign-launcher.md` (sonnet) — end-to-end campaign creation from property data to live ads. Walks user through audience research, creative, structure, and launch with approval gates at every step. Zero ads experience required.
- `agents/reflective-operator.md` (sonnet) — runs the daily loop end-to-end. Entrypoint for cron. Respects learning-phase guardrails from `data/launch-config.json`.
- `agents/lead-scorer.md` (haiku) — batch-scores new rows from the sheet. Cheap, frequent.
- `agents/creative-auditor.md` (sonnet) — on-demand creative fatigue / diversity / on-brand audit. Never pauses — proposes only.

## Google Sheets (the CRM)

Schema (13 columns, order matters):
```
timestamp | name | email | phone | interest | budget | timeline | message | source | score | status | notes | follow_up_date
```

Only `scripts/sheet-ops.py` talks to the sheet. Commands: `new`, `all`, `due`, `export`, `quality-by-adset`, `import-scores`. Requires `GOOGLE_SHEETS_KEY_FILE` and `LEAD_SHEET_ID` env vars.

## Attribution

Every landing-page link must carry UTM params plus an explicit `adset_id` (the Meta ad set ID — stable, survives campaign renames). `form-handler.gs` captures both; `sheet-ops.py quality-by-adset` prefers `adset_id` when present and falls back to `utm_campaign::utm_content` otherwise. Keep Meta ad set names stable; rename only via the `paid-ads` skill so the mapping stays consistent.

## Guardrails (non-negotiable)

1. **Lead-quality gate.** Never scale an ad set whose 14-day average lead score is below `kill_rules.min_avg_lead_score_for_scale_up` (×10 on the 0–100 scale). Cheap junk leads do not count toward winning ad sets. Override only by editing `data/kill-scale-rules.json` with intent + commit rationale.
2. **Daily budget cap.** `targets.daily_budget_cap_usd` is a hard stop. `loop-runner.sh` downgrades to `emergency_brake` when today's spend is within `cap_headroom_pct` (10%) of the cap. Cannot be bypassed mid-run.
3. **Approval-required actions** (never auto-executed): new campaigns, budget shifts >$50/day, targeting changes, audience expansions, disabling Advantage+. See `data/kill-scale-rules.json` → `approval_gates.escalate_actions`.
4. **Learning-phase protection.** If `data/launch-config.json` exists and `learning_phase.status == "active"`, restrict to pause/hold only. No audience changes, no budget changes >20%, no creative rotation (except force-pause for CTR <0.005 after $50 spend). Meta needs 14 days and ~50 Lead events to optimize delivery. Resetting the learning phase wastes the budget spent so far.

## Conventions

- **No AI slop in any output that touches a lead.** No "I hope this finds you well," no "nestled in," no "boasts," no "stunning," no em-dashes, no "exciting opportunity." Concrete, specific, first-person.
- Reference specific details from `data/property.json` in all ad copy and follow-ups. Never invent a fact.
- When scoring leads, always explain why in the notes field (≤280 chars).
- When reporting on campaigns, lead with the number that matters most (CPL or hot-lead count), then context.
- Budget values from the Meta Ads API are in cents — always convert for display.
- Every non-trivial ad decision appends to `data/ad-history.jsonl` and gets git-committed by the loop (`ops: YYYY-MM-DD N decisions, $X spend, Y leads, Z hot`).
- `data/property.json` placeholder check blocks `loop-runner.sh`. Populate before go-live.

## If in doubt

Check `docs/runbook.md` for escalation guidance, `docs/setup.md` for install steps, `docs/walkthrough.md` for how the parts fit together.
