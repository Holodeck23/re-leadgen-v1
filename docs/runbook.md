# Runbook

Operational guide for what to do when the reflective-ops loop escalates, when something breaks, or when a lead needs human intervention right now.

Everything here assumes the system is already set up (see `docs/setup.md`).

## How the loop runs

Every morning at 08:00, `scripts/loop-runner.sh` invokes the `reflective-operator` agent, which:

0. Checks `data/launch-config.json` for learning-phase status. If active, restricts to pause/hold only (see "First 2 weeks" below).
1. Reads the last N entries of `data/ad-history.jsonl` and the most recent ops git commit to recover context.
2. Pulls multi-timeframe Meta metrics (today / yesterday / 7d / lifetime) via the Pipeboard MCP.
3. Queries `python scripts/sheet-ops.py quality-by-adset` for per-ad-set average lead score over the last 14 days.
4. Invokes `ads-meta`, `analytics-tracking`, and `unicorn-promoter` skills for diagnostic reads.
5. Produces one `{action, hypothesis, confidence, revisit_trigger, requires_approval}` decision per ad set.
6. Auto-executes safe actions (pause, scale ±20%, refresh variant, hold). Appends to `data/ad-history.jsonl`. Git-commits `ops: YYYY-MM-DD N decisions, $X spend, Y leads, Z hot`.
7. Prints a morning briefing to stdout — hot leads first, then escalations, then a line on today's spend vs. cap.

Every 2 hours 08:00–20:00, a lighter `hot_sweep` mode runs steps 3 and 7 only — surfacing new hot leads fast without the full analysis cost.

## Morning briefing — what to look at first

The briefing is ordered so the top line is the thing that might need you *right now*. Read top-down until you've handled what's yours.

1. **🔥 Hot leads needing contact within 2h** — score ≥70. WhatsApp first. If you can't get to them, reply the one-line acknowledgement and schedule a real follow-up in Calendly.
2. **Escalations requiring approval** — any decision the loop parked. One-line hypothesis each. Approve, modify, or reject by replying in the same session (or by editing the proposed change before re-running).
3. **Executed actions** — things the loop already did. Skim unless a number looks wrong.
4. **Pipeline totals** — spend vs. cap, CPL, hot/nurture/cold counts, WoW delta.

## When to intervene

| Situation | What you do |
| --- | --- |
| Hot lead came in at 22:00 | Loop respects 22:00–07:00 quiet hours for outbound. You reply in the morning briefing window — or live if the deal warrants it. |
| Escalation "launch new campaign" | Review the hypothesis. If you agree, run `/skill paid-ads` with the proposal; if not, comment on the decision and it gets dropped. |
| Briefing says loop couldn't reach Meta | Check `/mcp` in a Claude session; refresh Pipeboard token if needed. Loop will retry next cycle. |
| Sheet quota error | Google Sheets API quota is 60 req/min per user. The script uses `batch_update` to stay under; if you see a burst, wait 60s and rerun. |
| Budget cap breach imminent | Loop bails into `emergency_brake` mode automatically when within `cap_headroom_pct` (10%) of `daily_budget_cap_usd`. All auto-execution stops; you get a one-line escalation. Raise the cap (with intent) or pause the worst offender. |

## The lead-quality gate (don't disable it)

The loop will not scale any ad set whose last-14-day average lead score is below `min_avg_lead_score_for_scale_up` (×10, because scores are on a 0–100 scale). This is the single most important guardrail — it prevents the Technically.dev failure mode (cheap clicks, unqualified leads, budget on fire).

If the loop keeps holding an ad set you want to scale:

1. Look at the scored leads in the sheet. Are they actually qualified (score ≥50)? If not, **the gate is working.**
2. Creative-audience mismatch is the usual cause. Either change the angle (investor vs. homebuyer vs. retiree) or tighten targeting.
3. Only bypass the gate if you have genuinely new information (e.g. a batch of unscored leads that are hot on reply). Bypass by editing `data/kill-scale-rules.json` with intent and commit the change — don't monkey-patch mid-run.

## Hot-lead response SLA

The system promises WhatsApp contact within 2 hours for any lead with `status=new` and hot-intent `interest` (lot / unit / investment). This is enforced two ways:

- `form-handler.gs` fires a real-time webhook to the endpoint set in script properties.
- The 2-hourly `hot_sweep` mode surfaces new hot leads with an `ALERT:` banner.

If you miss the SLA on a genuine hot lead:
1. Still reach out — a late reply converts better than none.
2. Reference something specific from their submission (interest + UTM context), not a generic "sorry for the delay."
3. Don't apologise twice.

## When a lead replies

`nurture-orchestrator` advances the lead through the matched sequence in `data/nurture-sequences.json` on every reply event. You or the loop tag the reply in the sheet `notes` column as `reply_positive`, `reply_negative`, or `reply_info_request`. The skill:

- re-runs `lead-qualifier` (BANT fields now populated) and updates `score`, `tier`, `segment`.
- cancels the calendar-fallback step if a milestone-trigger step is imminent.
- drafts the next message via `follow-up` skill (you approve before send unless you set auto-send in your own config).

## Creative refresh rotation

`ad-creative` and `ads-generate` work together:

- Every Monday, the loop's full daily run runs `ad-creative --mode iterate-from-performance` which reads the last 7 days of insights and proposes 6 new variants.
- New variants go into the variant library (not live yet). The loop auto-launches one from the library whenever a live ad hits the `refresh_creative_if` trigger in `data/kill-scale-rules.json` (CTR WoW drop >15% or frequency >2.5 at $50 spend).
- `unicorn-promoter` runs weekly, scanning organic posts for outliers to audition with $50.

## Incident response — common failure modes

### "The campaign launcher failed mid-way."
The `campaign-launch` skill saves progress to `data/launch-config.json` with `"status": "incomplete"` and `"failed_at_step": N`. Fix the issue (usually MCP auth or Pixel not firing), then re-run the launcher — it checks for existing campaigns and resumes from the failure point.

### "The loop paused everything overnight."
Something broke upstream (creative fatigue across the board, or Meta policy flag). Check `data/ad-history.jsonl` — every pause is logged with hypothesis. If the pauses were correct, queue creative refreshes. If they were false positives, the kill rules may be tuned too aggressive; inspect `data/kill-scale-rules.json`.

### "CPL is great but my phone isn't ringing."
The sheet is full of cheap junk. Check `quality-by-adset` — you'll see a low avg_lead_score. The gate is already holding the ad set flat. Change the angle or tighten targeting; don't scale.

### "A lead submitted twice and I contacted them twice."
`form-handler.gs` dedups on phone within 30 days and sets `status=duplicate`. Check the notes column — if you see `status=duplicate`, one of the two rows was a repeat. Reply once to the earlier row and move on.

### "Apps Script throwing quota errors."
Apps Script daily URL-Fetch quota is 20,000/day (paid) or 100/day (free). If you're hitting it, the hot-lead webhook is the usual culprit. Move it to a dedicated Cloudflare Worker or Lambda receiver — leave the rest of the Apps Script on its native quota.

### "I need to pause everything NOW."
```bash
./scripts/loop-runner.sh emergency_brake
```
Loop pauses all active ad sets, appends a `brake` event to `data/ad-history.jsonl`, and exits. Reversing is a manual `paid-ads` run — intentional friction.

## First 2 weeks after launch (the learning phase)

Meta's algorithm needs about 14 days and 50 Lead events to optimize delivery. During this window the system restricts itself automatically.

**If you used the campaign launcher** (recommended): it already set up the hybrid cold-start strategy (60% manual targeting + 40% Advantage+), wrote `data/launch-config.json` with the learning-phase guardrails, and configured `reflective-ops` Step 0 to enforce them. The morning briefing shows a banner: `⚠ LEARNING PHASE ACTIVE — day N of 14, X/50 Lead events.` You don't need to do anything special — just respond to hot leads and approve escalations as usual.

**If you launched manually**: the same rules apply, but you need to be disciplined:
- Do NOT change audiences or targeting — it resets the learning phase
- Do NOT change budgets by more than 20% per ad set
- Do NOT rotate creative unless an ad is clearly failing (CTR <0.5% after $50 spend)
- The quality gate will hold everything flat on thin data — this is expected, not broken
- Switch from manual-only to Advantage+ after you have ~50 conversion events

**What happens when learning phase ends:**
- `reflective-ops` detects the exit criteria (14 days elapsed OR 50 Lead events) and updates `data/launch-config.json` → `learning_phase.status` to `"exited"`
- Morning briefing announces: `✓ LEARNING PHASE COMPLETE — full optimization unlocked.`
- Full action vocabulary unlocks: scale, creative refresh, launch variant
- CBO consolidation becomes available when ≥2 ad sets are winning (CPL below target + lead quality above gate + 3 consecutive profitable days)

## Weekly review cadence (30 minutes, Friday)

1. Read the last 7 days of `data/ad-history.jsonl` — do the decisions still make sense?
2. Skim the morning briefings — which escalations did you approve? Were they right?
3. Check `quality-by-adset` over 14d — any ad set gaming the CPL metric with junk?
4. Check `unicorn-promoter` output — is organic content producing outliers? If not, the angle is stale.
5. Quick Ad Library scan (5 min) — search your market for new competitor ads. Paste anything interesting into a Claude session and say "analyze these competitor ads" to run the `competitive-intel` skill. Long-running competitor ads that match angles you haven't tested = creative opportunity.
6. Update `data/kill-scale-rules.json` if a threshold feels wrong. Commit with intent, short rationale in the message.

## Monthly review (60 minutes, first of the month)

1. Revisit `data/scoring-model.json` weights. Run `sheet-ops.py all | ...` to compute score correlation with closed deals; adjust weights if obvious signal is being missed.
2. Submodule bump: `git submodule update --remote vendor/claude-ads vendor/marketingskills` — review the upstream changelog, merge deliberate improvements into your patched skills, commit.
3. Archive `data/ad-history.jsonl` if it's over 10k lines (rename with timestamp, empty file, keep last 30 days inline).
4. Rotate Meta + Pipeboard tokens per security policy.

## When to escalate to the owner / sales

The loop handles marketing and lead-ops. It does not handle:

- Actual sales calls.
- Pricing / promotion negotiations.
- Legal / title / contract questions.

Whenever a lead asks about pricing beyond the published range, title specifics, financing terms, or timeline commitments — route to the human by setting `status=handoff` and `notes=<what they asked>`. The human reads handoffs daily.

## What good looks like, numerically

- CPL trending down WoW on the winners; flat on junk (quality gate working).
- Hot-lead SLA ≥ 90% (contact within 2h).
- Creative refresh cadence at least weekly per active ad set — fatigue rarely visible in the `ads-meta` output.
- `data/ad-history.jsonl` gets a new entry every day.
- Your Friday review catches 1–3 adjustments per week, not 20 — the system should be running itself most of the time.
