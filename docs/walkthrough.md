# System Walkthrough

A guided tour of every moving part in this repo, what it does, how it connects to the others, and why it is shaped the way it is. Read this end-to-end the first time. After that, treat it as a map you come back to when something escalates.

If you want the install steps instead, jump to `docs/setup.md`. If you want the on-call guide for when the loop needs you, see `docs/runbook.md`.

## Table of contents

1. [What this system is](#what-this-system-is)
2. [The design principles that decided the shape](#the-design-principles-that-decided-the-shape)
3. [Architecture at a glance](#architecture-at-a-glance)
4. [The daily loop — what actually happens](#the-daily-loop--what-actually-happens)
5. [The lead journey — from ad to sold](#the-lead-journey--from-ad-to-sold)
6. [File-by-file tour](#file-by-file-tour)
7. [The guardrails that keep this from burning money](#the-guardrails-that-keep-this-from-burning-money)
8. [How you interact with the system day-to-day](#how-you-interact-with-the-system-day-to-day)
9. [Extending it](#extending-it)

---

## What this system is

An autonomous Meta-ads + lead-gen operator for real estate. One person plus a daily loop replaces what would otherwise need a media buyer, a marketing coordinator, and a BDR. The humans do what humans are good at (sales calls, pricing decisions, contracts). The loop does what it is good at (scoring every lead the same way every day, pulling Meta metrics without forgetting a timeframe, pausing an ad with a bad hook rate at 4am, logging every decision so next week's decisions can learn from this week's).

The system generalises to any property listing — swap `data/property.json`, refresh the Meta pixel, go.

The stack is deliberately simple:
- **Landing page:** static HTML + JS, reads `property.json` at runtime, three-field lead form.
- **CRM:** Google Sheets, 13 columns.
- **Ad platform:** Meta (FB/IG), driven by the Pipeboard MCP.
- **Brain:** Claude Code, running a set of skills daily via a cron-invoked agent.
- **State:** git. Every ad decision appends to `data/ad-history.jsonl` and gets committed. The repo *is* the operational memory.

No app to deploy, no server to maintain, no database to migrate. The moving parts are: a static site, a spreadsheet, a Meta ad account, a handful of markdown files that tell Claude how to behave, and a shell script on cron.

## The design principles that decided the shape

Seven principles shaped every file in the repo. When you change something, check it still honours these.

1. **Creative first, targeting second.** In 2026 Meta's Advantage+ engine does more of the targeting for you; the lever you still control is the hook, the angle, and the offer. Every A/B test runs a hook × angle × offer matrix, and `ads-meta` audits for creative fatigue and near-duplicate suppression (Andromeda throttles creatives with >60% visual similarity).
2. **Unicorn promotion.** Post 15–20 assets organically, then promote only the top-decile hook/CTR outliers. Cents-per-click, not dollars — they inherit organic relevance. `skills/unicorn-promoter/` implements this.
3. **Published kill and scale thresholds.** Pause when frequency >3.0, CTR <0.8% after $50 spend, or CPL >2× target with ≥10 leads. Scale +20% after 3 consecutive days below CPL target with average lead score ≥5. Refresh creative when CTR drops 15% WoW. Encoded in `data/kill-scale-rules.json` — single source of truth, read by multiple skills.
4. **Lead quality gates every scaling decision.** Cheap clicks that don't become qualified leads are not a win. The loop will not scale an ad set whose 14-day average lead score is below the gate, regardless of how good the CPL looks. This is *the* differentiator from generic "Claude runs Meta ads" systems that optimise for cheap junk.
5. **BANT + behavioural + property-fit scoring.** Pre-approval or cash (+30), budget in range (+20), timeline <30 days (+25), specific lot or unit named (+15), reply within 5 minutes (+10), return visit (+10), engaged with first follow-up (+15). Score ≥70 hot, 40–69 nurture, <40 long-cycle. Tuneable in `data/scoring-model.json`.
6. **Milestone-triggered nurture, not calendar drip.** People don't respond to day-14 check-ins; they respond to new information. The sequences in `data/nurture-sequences.json` fire on events (new drone footage, construction milestone, lot sold in same phase, price change, comparable sale nearby). Calendar fallbacks exist so nobody falls through, but they are the backstop, not the plan.
7. **Audit trail as memory.** Every loop iteration reads the last N entries of `data/ad-history.jsonl` and the most recent ops commit before deciding anything. Fresh-context sessions stay coherent because the repo remembers what the last session decided and why.

## Architecture at a glance

```
                          ┌────────────────────┐
                          │  data/property.json │   single source of truth
                          └─────────┬──────────┘
                                    │
           ┌────────────────────────┼────────────────────────┐
           │                        │                        │
     ┌─────▼─────┐           ┌──────▼──────┐           ┌─────▼─────┐
     │ site/     │           │  skills/    │           │  agents/  │
     │ index.html│           │  (Claude)   │           │           │
     │ form-     │           │             │           │ campaign- │
     │ handler.gs│           │  campaign-  │           │  launcher │
     │ thank-you │           │   launch    │           │           │
     └─────┬─────┘           │  audience-  │           │ reflective│
           │                 │   research  │           │  -operator│
           │                 │  reflective │           │           │
           ▼                 │  -ops       │           │ creative- │
   ┌──────────────┐          │  lead-      │           │  auditor  │
   │ Google Sheet │          │   qualifier │           │           │
   │   (the CRM)  │◄─────────┤  follow-up  │           │ lead-     │
   └──────┬───────┘          │  nurture-   │◄──────────┤  scorer   │
          │                  │   orchestr. │           └───────────┘
          │                  │  ad-creative│
          │                  │  paid-ads   │──►┌───────────────────┐
          │                  │  ads-meta   │   │  Meta Ads MCP     │
          │                  │  (and 6 more)│   │  (via Pipeboard)  │
          │                  │             │   └───────────────────┘
          │                  └──────┬──────┘
          │                         │
          │                         ▼
          │                  ┌─────────────┐
          └─────────────────►│ data/       │
                             │ ad-history  │   append-only log
                             │  .jsonl     │   + git commits
                             └─────────────┘
                                    ▲
                                    │
                             ┌──────┴──────┐
                             │ cron / MCP  │
                             │ scheduler   │
                             │             │
                             │ loop-       │
                             │  runner.sh  │
                             └─────────────┘
```

- **Landing page → Google Sheet:** a visitor fills the three-field form, `form-handler.gs` writes a row, and if the intent looks hot, fires a real-time webhook.
- **Sheet → skills:** every skill that reads lead data goes through `scripts/sheet-ops.py` — one abstraction so quota and shape stay consistent.
- **Skills → Meta:** ad actions go through the Pipeboard MCP. No direct Meta API calls from Claude.
- **Skills → audit:** every non-trivial decision appends to `data/ad-history.jsonl` and gets git-committed by the loop.
- **Scheduler → brain:** cron (or the `scheduled-tasks` MCP) fires `scripts/loop-runner.sh`, which invokes the `reflective-operator` agent headless.

## The daily loop — what actually happens

The heart of the system is one skill (`skills/reflective-ops/`), one agent that drives it (`agents/reflective-operator.md`), and one script that schedules it (`scripts/loop-runner.sh`).

Once a day at 08:00 local, cron runs `./scripts/loop-runner.sh`. Preflight:
- `data/property.json` exists and contains no `UPDATE` placeholders.
- Required env vars are set.
- Today's Meta spend is more than 10% below the daily cap; otherwise the run downgrades itself to `emergency_brake` mode and sits on its hands.

Then `loop-runner.sh` invokes the `reflective-operator` agent with the `reflective-ops` skill. The agent:

1. **Recovers context.** Reads the tail of `data/ad-history.jsonl` and the most recent `ops:` git commit to see what yesterday's loop decided and why.
2. **Pulls multi-timeframe Meta metrics** via the Pipeboard MCP — today, yesterday, 7d, lifetime for every active ad set. Never trusts single-day data; single-day CPL spikes lie.
3. **Pulls the lead-quality signal** — `python scripts/sheet-ops.py quality-by-adset --window-days 14` returns average lead score per ad-set. Attribution key is Meta's `{{adset.id}}` URL macro (captured by the landing page and written to the notes column); UTM parsing is the fallback for organic/referral traffic and legacy rows. Renaming a campaign or ad in Meta does not break the gate. This is the gate.
4. **Runs diagnostic skills in parallel** — `ads-meta` (creative fatigue, audience overlap, pixel/CAPI health), `analytics-tracking` (funnel integrity), `unicorn-promoter` (organic outliers to audition).
5. **Decides**, per ad set: `{action, hypothesis, confidence, revisit_trigger, requires_approval}`. Actions: `pause` (kill rule hit), `scale_up_20` (3-day winner with quality-gate pass), `scale_down_20`, `refresh_creative` (CTR WoW drop or frequency), `expand_audience` (always escalates), `hold`, `launch_variant`.
6. **Plans execution order.** Pauses first (stop the bleed), then scale-downs, then refreshes, then scale-ups. This order minimises the window where the account is bleeding.
7. **Executes auto-approved actions.** Auto-approved: pause on kill rule, ±20% scaling with quality-gate pass, refreshing to a pre-generated variant, and hold. Everything else escalates to the morning briefing for you to approve.
8. **Logs every decision** to `data/ad-history.jsonl` and commits with `ops: YYYY-MM-DD N decisions, $X spend, Y leads, Z hot`.
9. **Prints the morning briefing** — hot leads first (you need to contact them within 2 hours), then escalations, then executed actions, then pipeline totals.

Every 2 hours 08:00–20:00, a lighter `hot_sweep` mode runs steps 3 and 9 only — it surfaces new hot leads without the full analysis cost, so the 2-hour SLA is enforceable without burning 6 full loops per day.

## The lead journey — from ad to sold

### 1. Meta ad → landing page

An ad sends a visitor to the landing page with UTM params. `site/index.html`:
- Fetches `property.json` at runtime and hydrates every price, inventory count, location, amenity, photo, and contact link.
- Fires the Meta Pixel `PageView` event and `ViewContent` when the visitor scrolls past the hero.
- Captures the `adset_id` URL param (set by Meta's `{{adset.id}}` macro), the UTM params, `document.referrer`, a `rlg_visited` localStorage flag, and the `user_agent` / `page` URL for the Conversions API payload.
- Generates a `crypto.randomUUID()` event ID that will deduplicate the Pixel event against the server-side CAPI event later.

### 2. Form submit → Google Sheet

The form has exactly three visible fields: name, phone (WhatsApp preferred), and an interest dropdown. No email, no budget, no message — per the Baymard form-length research. `site/form-handler.gs`:
- Validates: name ≥2 chars and contains no URL; phone ≥8 digits after stripping non-digits; interest in the known set.
- Deduplicates: if the same phone (digit-normalised) submitted within the last 30 days and the status isn't `closed` or `lost`, sets `status=duplicate` instead of `new`.
- Writes the row: name, phone, interest, UTM source (pipe-delimited), and a notes field containing the lead ID (== event ID), return-visitor flag, and `adset_id` when present.
- Fires a real-time webhook to `HOT_LEAD_WEBHOOK_URL` if the interest is `lot`, `unit`, or `investment`.
- Fires a server-side Meta Conversions API `Lead` event (hashed phone + hashed `external_id` + `user_agent`) with the same `event_id` the browser Pixel used — so client and server events dedup in Events Manager.
- Returns `{status, lead_id, event_id}` to the landing page, which redirects to `site/thank-you.html?lead_id=…&event_id=…&interest=…`.

### 3. Thank-you page → conversion event + progressive disclosure

`site/thank-you.html`:
- Fires the Pixel `Lead` event with the same event ID as the server-side CAPI event — they dedup in Events Manager.
- If the interest was hot, shows a Calendly embed and a WhatsApp CTA hydrated from `property.json`.
- Shows a one-field email form for the brochure — progressive disclosure: the visitor already committed by submitting the main form, so the psychological cost of one more field is low. Converts on average at 40–60% in RE. On submit the form POSTs `{action: "progressive_email", lead_id, event_id, email}` to the same Apps Script endpoint, which writes the email into the row and fires a server-side `CompleteRegistration` CAPI event (hashed email + external_id).

### 4. Sheet row → lead-scorer agent → hot alert

On the next loop tick (hot_sweep every 2h), `agents/lead-scorer.md` reads new rows from the sheet, invokes `skills/lead-qualifier/` per row, and produces scored records. For any row with score ≥70 or hot-interest, it emits an `ALERT: N hot leads need contact within 2 hours` line in the briefing.

### 5. Follow-up → nurture → close

For hot leads, `skills/follow-up/` drafts a WhatsApp message (≤3 sentences) plus a longer email, referencing a specific lot/unit if named and a specific property detail from `property.json`. You approve and send.

For everyone, `skills/nurture-orchestrator/` keeps the lead in the right sequence from `data/nurture-sequences.json`. Sequences fire on milestones (new drone footage, a lot sold in the same phase, construction progress, price announcements). Calendar fallbacks exist but are the backstop. On reply, the orchestrator re-invokes `lead-qualifier` (now with BANT fields populated from the conversation) and may promote or demote the lead's tier.

### 6. Close → status update → quality feedback

Once you close a deal (or lose it), you tag the sheet row `closed` or `lost`. The next `quality-by-adset` query includes that outcome; over time the gate's inputs get richer and the system starts scaling the ad sets that produce closers, not just scorers.

## File-by-file tour

### `data/`

- **`property.json`** — the canonical listing. Every lead-facing piece of copy reads from here via the `property-context` skill. Created from `property.example.json` during setup; the loop refuses to run until every `UPDATE` placeholder is replaced with real content.
- **`kill-scale-rules.json`** — pause/scale/refresh thresholds, auto-approval list, statistical guardrails (minimum impressions, minimum leads, minimum spend before judgement), and learning-phase restrictions (first 14 days or 50 Lead events — blocks scale/audience/creative changes so Meta's algorithm can optimize). Edit deliberately.
- **`launch-config.json`** — created by the `campaign-launch` skill when you first go live. Records every campaign and ad set ID, the audience research snapshot, creative library snapshot, and learning-phase state (start date, event count, status). `reflective-ops` reads this to enforce learning-phase restrictions and know when to unlock full optimization. Do not edit during the learning phase.
- **`scoring-model.json`** — the BANT + behavioural + property-fit weights. Tune weekly based on the correlation between lead score and closed deals.
- **`nurture-sequences.json`** — tier-matched message sequences with milestone triggers.
- **`ad-history.jsonl`** — append-only decision log. One JSON object per line. The loop reads the tail to recover context.

### `skills/`

The skill set splits into three layers:

**Foundation (RE-specific, invoked by many others):**
- `property-context/` — reads `property.json` and emits a Context Block plus the anti-slop writing rules. Every lead-facing skill invokes this first. Blocks loudly if `property.json` still has `UPDATE`.

**Campaign creation (zero to live):**
- `campaign-launch/` — the 9-step sequence that takes someone with zero ads experience from "property data filled in" to "Meta campaigns running." Validates data, checks Pixel health, researches audiences (via `audience-research`), generates creative with 6 psychological hook categories, builds campaign structure with Housing Special Ad Category compliance, runs a 17-item pre-launch checklist, creates everything via the Meta Ads API (paused), writes `data/launch-config.json` with learning-phase guardrails, and goes live only on explicit user approval.
- `audience-research/` — builds Meta ad targeting from property data alone. Produces segment-specific interest stacks (investor, homebuyer, retiree, expat), location targeting (primary radius + feeder cities + international markets), a hybrid cold-start strategy (60% manual targeting + 40% Advantage+), life-event targeting layers, and retargeting/exclusion audiences. Full Housing Special Ad Category compliance: no ZIP targeting, no gender selection, no age narrowing below 18 or above 65, minimum 15-mile radius.

**RE-rewritten core:**
- `lead-qualifier/` — scores a lead against `scoring-model.json`. Returns tier, segment (investor / homebuyer / retiree / expat / generic), and a ≤280-char notes line.
- `follow-up/` — drafts WhatsApp (≤3 sentences) and email (5–8 sentences) per segment. WhatsApp-first for hot leads; email-first when sending artefacts.
- `nurture-orchestrator/` — advances a lead through the right sequence, fires on milestones or replies, respects quiet hours and rate limits.
- `unicorn-promoter/` — reads 30 days of organic post metrics, ranks by hook-rate + CTR percentile, flags the top decile, proposes $50 auditions. Requires approval.
- `reflective-ops/` — the daily loop. Described above.

**Vendored + patched (from `vendor/marketingskills` and `vendor/claude-ads`):**
- `ad-creative/` — generate-mode and iterate-from-performance mode; produces 6 Meta variants (2 Feed, 2 Reels, 1 Carousel, 1 Retargeting). Enhanced with 6 psychological hook categories: curiosity gap, social proof, specificity, loss aversion, identity, and pattern interrupt.
- `competitive-intel/` — analyze competitor ads from the public Meta Ad Library. Classifies each ad by hook type, angle, segment, format, and longevity. Produces pattern reports (hook/angle/visual distributions) and inspiration seeds (adapted to your property data, never copied). Feeds into `ad-creative`. Recommended cadence: before first launch (seed initial creative), weekly during Friday review.
- `paid-ads/` — Meta-only, `OUTCOME_LEADS` objective, daily-budget cap hard stop. Housing Special Ad Category mandatory on every campaign.
- `analytics-tracking/` — Pixel + CAPI priorities, UTM capture, quality-by-adset query.
- `ab-test-setup/` — hypothesis format (IF/THEN/BECAUSE/REVISIT), 1000-impression / 10-lead / $50-spend minimums.
- `page-cro/` — drone video hero, 3-field form, 3 testimonials, FAQ, sticky mobile CTA.
- `form-cro/` — exactly three fields, hidden UTM capture, 30-day phone dedup.
- `ads-meta/` — creative fatigue, audience overlap, pixel/CAPI health audit.
- `ads-generate/` — image generation; prefers real photography from `property.json` over AI.

Each vendored skill has a patch block at the top that overrides upstream defaults with real-estate-specific rules, without editing the original body. This keeps upstream updates mergeable.

### `agents/`

- **`campaign-launcher.md`** (sonnet) — end-to-end campaign creation agent. Orchestrates the `campaign-launch` skill through all 9 steps with user approval gates at audience research, creative review, campaign structure, and go-live. Designed for users with zero ads experience. Creates everything PAUSED, explains every decision in plain language, only goes live on explicit confirmation.
- **`reflective-operator.md`** (sonnet) — runs the daily loop end-to-end. Given mode (`full`, `hot_sweep`, `dry_run`, `emergency_brake`), it invokes `reflective-ops` with the right tool permissions. Now includes Step 0: learning-phase check that reads `data/launch-config.json` and restricts actions during the first 14 days / 50 Lead events.
- **`lead-scorer.md`** (haiku) — batch-scores new leads from the sheet. Cheap model, frequent invocation, one ALERT banner per hot lead.
- **`creative-auditor.md`** (sonnet) — wraps `ads-meta` for on-demand creative fatigue / diversity / on-brand audits. Never auto-pauses; it's a second-opinion tool.

### `scripts/`

- **`onboard.sh`** — interactive setup wizard. Walks a new user through every step: property data, Google credentials, sheet creation, Apps Script, Meta Pixel, env vars. Runs preflight at the end. Idempotent — skips steps already completed.
- **`preflight.sh`** — pre-launch validation. Checks all 16 prerequisites and prints pass/fail with exact fix instructions. Run this before going live and after any config change.
- **`create-sheet.py`** — creates a Google Sheet with the correct 13-column schema, data validation dropdowns (status, interest), conditional formatting (hot leads highlighted green, duplicates greyed out), and column widths. Shares with the user's email. Used by `onboard.sh` or standalone.
- **`sheet-ops.py`** — the only thing that talks to the Google Sheet at runtime. Commands: `new`, `all`, `due`, `export`, `quality-by-adset`, `import-scores`. Uses `batch_update` for writes (one API call per batch).
- **`meta-insights.py`** — standalone Meta Graph API client for when cron runs don't have the MCP. Pulls four timeframes (today / yesterday / 7d / lifetime), derives hook rate and CPL. Used as a fallback; the normal path is the Pipeboard MCP inside a Claude session.
- **`loop-runner.sh`** — entrypoint for cron. Preflights, reads the budget cap, invokes `claude --print --agent reflective-operator`.

### `site/`

- **`DESIGN.md`** — visual design system for the landing pages. Defines color tokens (warm off-white + earthy gold accent), typography scale (system fonts, fluid sizing), spacing system, component specs (hero, form, cards, FAQ, mobile CTA), photography direction, and performance targets (<2.5s LCP, <500KB). Read by `page-cro` before any markup changes. Accent color overridable via `property.json → branding.accent_color`.
- **`index.html`** — property.json-hydrated landing page, 3-field form, Pixel init, UTM + return-visitor capture, event-ID dedup, sticky mobile CTA.
- **`form-handler.gs`** — the Apps Script behind the form. Validation, dedup, webhook fire-and-forget.
- **`thank-you.html`** — post-submit page with conditional Calendly, progressive email capture, Pixel conversion event.

### `docs/`

- **`HANDOFF.md`** — cold-start entry point; designed for someone picking up this repo for the first time. Recommends the setup wizard as the fastest path and the campaign launcher for go-live.
- **`setup.md`** — step-by-step install guide.
- **`runbook.md`** — the on-call guide: what to do when the loop escalates or breaks.
- **`walkthrough.md`** — this file.

### `vendor/`

Git submodules pinned to specific SHAs:
- `vendor/claude-ads` — source for `ads-meta/` and `ads-generate/`.
- `vendor/marketingskills` — source for the six marketing-skill copies.

Reference only — never edited. When upstream ships something worth taking, bump the submodule, review the diff, copy any improvements into the patched skill in `skills/`.

### `tests/fixtures/`

Test fixtures (`hot_lead_payload.json`, `synthetic_kill_insight.json`, `synthetic_decisions.jsonl`) used to dry-run the form validation + scoring pipeline and the kill-rule + quality-gate pipeline without touching live credentials.

## The guardrails that keep this from burning money

Four things prevent the default failure mode of autonomous ad systems — optimising hard for the wrong metric.

### 1. The lead-quality gate

Encoded in `kill-scale-rules.json` → `kill_rules.min_avg_lead_score_for_scale_up = 5.0` (on the 1–10 rubric; translated to 50.0 on the 0–100 scoring-model scale). Before any scale-up, the loop queries `quality-by-adset` for the last 14 days of leads per UTM-derived ad-set key and requires the average score to be above the gate. A cheap ad set that produces score-14 junk gets held, not scaled, regardless of CPL.

This is the guardrail that keeps "cheap clicks" from turning into "cheap worthless leads."

### 2. The daily budget cap

`kill-scale-rules.json` → `targets.daily_budget_cap_usd`. `loop-runner.sh` reads this at preflight; if today's Meta spend is within `cap_headroom_pct` (10%) of the cap, the loop downgrades to `emergency_brake` — it can still pause things, it cannot scale or launch. An actual cap breach is simply impossible because the loop cannot step outside the rules it reads at startup.

### 3. Learning-phase protection

When you first launch campaigns (via the `campaign-launch` skill or manually), Meta's algorithm needs about 14 days and 50 Lead events to learn who converts. During this learning phase, changes to audiences, large budget shifts, or creative rotation reset the algorithm and waste the budget spent so far.

`data/launch-config.json` tracks learning-phase state (start date, event count, status). `reflective-ops` Step 0 reads it and restricts the action vocabulary to `pause` and `hold` only. Exception: an ad with CTR <0.005 after $50 spend gets force-paused even during learning — it's clearly failing. Once the learning criteria are met, the system auto-unlocks full optimization and notes it in the morning briefing.

The learning-phase rules live in `data/kill-scale-rules.json` → `learning_phase`.

### 4. Housing Special Ad Category

All real estate ads on Meta must declare `special_ad_categories: ["HOUSING"]`. This restricts targeting: ages 18–65+ only, all genders, no ZIP/postal code targeting, minimum 15-mile location radius, no income/net-worth/credit-score interests. Violating this causes ad rejection or account restriction.

This requirement is enforced in `audience-research`, `campaign-launch`, and `paid-ads` skills.

All four guardrails are edited by changing a JSON file and committing with intent — they cannot be monkey-patched mid-run.

## How you interact with the system day-to-day

Three touch points:

1. **Morning briefing** (cron output, or paste `scripts/loop-runner.sh` stdout into a Claude session). 60 seconds. Contact hot leads, approve escalations, skim the rest.

2. **Hot-lead pings** (every 2 hours). A message saying "ALERT: 2 hot leads need contact within 2 hours." You WhatsApp them.

3. **Weekly review** (Friday, 30 minutes). Read the week's `ad-history.jsonl`, check `quality-by-adset` trends, glance at `unicorn-promoter` output, adjust thresholds in `kill-scale-rules.json` or weights in `scoring-model.json` if something looks off. Commit with a one-line rationale.

Everything else runs itself. If you're touching the system every day beyond those three, something is wrong — either the thresholds are too aggressive (you're approving too many escalations) or too loose (you're correcting too many auto-executions). Adjust and commit.

## Extending it

### Adding a new audience segment

1. Add it to `data/scoring-model.json` → `audience_segments` with `signals` (keywords that classify a lead into this segment) and a `pitch` string.
2. Add a content spine to `skills/follow-up/SKILL.md`.
3. Add a sequence to `data/nurture-sequences.json` if the tier-default isn't right.
4. Generate segment-specific ad variants via `skills/ad-creative/`.

### Adding a new property

1. Duplicate the repo (or add a `properties/` dir if you want to multiplex — but start with one).
2. Populate the new `property.json`.
3. Run `./scripts/onboard.sh` to set up the CRM, Pixel, and env vars.
4. Open Claude Code and say "Launch my campaigns" — the campaign launcher researches audiences, generates creative, builds campaign structure, and walks you through going live. Zero ads experience required.

### Swapping the CRM

Only `scripts/sheet-ops.py` talks to the sheet. Write a new driver with the same CLI shape (`new | all | due | export | quality-by-adset | import-scores`) and nothing else changes.

### Adding SMS (Twilio)

Out of scope for v1 — WhatsApp is enough for the current geography. When you need it: add a channel strategy to `skills/follow-up/SKILL.md` and a Twilio invocation to `form-handler.gs`'s hot-lead webhook endpoint (or wherever you wire the real-time alerts). The rest stays.

### Multi-language

Add a `locale` field to `property.json`, thread it through `property-context`, and duplicate the relevant content keys. Start with English + Spanish for Latin America.
