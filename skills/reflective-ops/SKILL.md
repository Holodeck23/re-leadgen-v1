---
name: reflective-ops
description: The daily brain. Runs the analyze → iterate → execute loop for Meta ad performance with lead-quality as the gating signal. Recovers context from prior runs, pulls multi-timeframe metrics, invokes ads-meta + analytics-tracking + unicorn-promoter, produces structured decisions with hypothesis + confidence, auto-executes safe actions, escalates the rest, logs everything to data/ad-history.jsonl, and writes a scannable morning briefing. Invoked by agents/reflective-operator.md or scripts/loop-runner.sh.
user-invokable: true
---

# Reflective Ops — the daily ad-performance loop

You are the operator. Every day (and every 2h in hot-lead-sweep mode), you execute the same 8-step loop. Context is recovered from the repo itself — never assume prior state.

## Operating principle

The single most important thing: **lead quality gates every scaling decision**. A cheap lead that does not score ≥5 on `data/scoring-model.json` does not count toward "this ad set is winning." The loop must be faster at killing bad campaigns than at scaling good ones.

## Modes

| Mode | Cadence | Steps executed | Auto-execute |
|---|---|---|---|
| `full` | daily | 1–8 | safe actions only |
| `hot_sweep` | every 2h | 3 + 8 (subset) | none (alert only) |
| `dry_run` | on demand | 1–6, 8 (skip 7 execute) | never |
| `emergency_brake` | on demand | halt all scale-ups, pause everything at frequency >3 | pause only |

## Step 0 — Check learning phase

Before anything else, check if `data/launch-config.json` exists and if we are in a learning phase:

1. Read `data/launch-config.json`. If it doesn't exist, skip this step (no campaigns launched yet via campaign-launcher).
2. If `learning_phase.status == "active"`:
   - Check `do_not_edit_until` date. If today < that date AND `learning_phase.events_so_far < learning_phase.target_events_for_exit`:
     - **Learning phase is active.** Restrict the action vocabulary to `pause` and `hold` only. Read `kill-scale-rules.json.learning_phase.allowed_actions_during_learning`.
     - Exception: force-pause is allowed if CTR < 0.005 after $50 spend (see `learning_phase.exception`).
     - Add a banner to the briefing: `⚠ LEARNING PHASE ACTIVE — day {N} of 14, {events_so_far}/{target_events_for_exit} Lead events. Actions restricted to pause/hold.`
   - If today ≥ `do_not_edit_until` OR events_so_far ≥ target_events_for_exit:
     - Update `learning_phase.status` to `"exited"` in launch-config.json.
     - Add to briefing: `✓ LEARNING PHASE COMPLETE — full optimization unlocked.`
     - Check if CBO consolidation is available (≥2 winning ad sets per `learning_phase.cbo_consolidation_available_after`).

## Step 1 — Recover context

Read:
- Last 50 entries from `data/ad-history.jsonl` (append-only log; each line is one prior decision).
- Last 20 git commits in the repo (the commit messages encode prior daily summaries: `ops: 2026-04-20 12 decisions, $147 spend, 4 leads, 1 hot`).
- Current state of `data/kill-scale-rules.json` and `data/scoring-model.json` (rules may have been updated).
- `data/launch-config.json` if it exists (learning-phase state, original targeting snapshot).
- `property-context` skill output (STOP if BLOCKED).

Build a 1-paragraph context summary: "Yesterday spent $X, got N leads, avg score Y. Ad sets A and B scaled +20% and held; ad set C was paused for frequency. Two escalations pending human approval from yesterday: [...]."

## Step 2 — Pull multi-timeframe metrics

Use `scripts/meta-insights.py` (or Meta Ads MCP directly if the script is unavailable). For every active ad set, pull insights across 4 timeframes:
- `today` (so far)
- `yesterday` (full day)
- `last_7_days`
- `lifetime` (since campaign launch)

Required metrics per ad set:
`spend, impressions, reach, frequency, clicks, ctr, cpm, cpc, leads, cpl, hook_rate_3s (video), hold_rate (video)`.

**Never judge on a single timeframe.** Compare `yesterday` vs `last_7_days` to detect acute drops; compare `last_7_days` vs `lifetime` to detect trend.

## Step 3 — Lead-quality signal

Call `python scripts/sheet-ops.py quality-by-adset` (implemented in Phase 5). Returns:
```json
{
  "as_of": "2026-04-21T09:15:00Z",
  "window_days": 14,
  "by_adset": [
    { "adset_id": "...", "adset_name": "...", "leads": 23, "avg_score": 6.4, "hot_count": 7, "qualified_rate": 0.57 }
  ]
}
```

In `hot_sweep` mode, this is the only metric source. Surface any new leads with score ≥70 that have not been contacted yet — that's the entire output.

## Step 4 — Analyze

Invoke in parallel:
- `ads-meta` — account health + 50-check audit against this data.
- `analytics-tracking` — Pixel/CAPI dedup rate, UTM integrity, funnel drop-off.
- `unicorn-promoter` — weekly cadence only; skip on other days.

Each returns a finding list. Deduplicate findings that point at the same ad set for the same cause.

## Step 5 — Decide

For each ad set, produce exactly one `Decision`:

```json
{
  "adset_id": "...",
  "adset_name": "...",
  "current_daily_budget_usd": 45,
  "observed": { "cpl": 32, "ctr": 0.011, "frequency": 2.1, "avg_lead_score": 6.1, "leads_14d": 18 },
  "action": "scale_up",
  "action_detail": { "new_daily_budget_usd": 54, "delta_usd": 9 },
  "hypothesis": "Under target CPL 3 consecutive days with avg lead score 6.1 > gate 5.0. Scaling +20% is within max_auto_scale_per_day.",
  "confidence": 0.82,
  "revisit_trigger": "if CPL > 40 for 2 days OR avg_lead_score drops below 5 on next 10 leads, scale down and re-examine creative fit",
  "requires_approval": false,
  "auto_approved_reason": "action=scale_up, passes lead-quality gate, within daily_budget_cap headroom"
}
```

**Action vocabulary:**
`pause | scale_up | scale_down | refresh_creative | expand_audience | hold | launch_variant | new_campaign | disable_advantage_plus`

**Auto-approval rules (from `data/kill-scale-rules.json.approval_gates`):**
- Auto-approved: `pause, scale_up (within cap), scale_down, refresh_variant, hold` — AND lead-quality gate passes (for scale_up only).
- Escalate: `expand_audience, new_campaign, budget_shift > $50/day, targeting_change, disable_advantage_plus`.

**Confidence calibration** (not feelings — use these anchors):
- `1.0`: A deterministic kill rule fired (e.g., frequency 3.5 with $80 spend).
- `0.8–0.9`: Multi-timeframe data agrees, sample size sufficient (n≥10 leads OR ≥$50 spend).
- `0.5–0.7`: Directional signal, small sample, recommend hold or small change.
- `<0.5`: Don't act. Log the observation, set `action=hold`.

**Budget cap enforcement:** Before producing any `scale_up` or `launch_variant` action, compute projected total daily spend across all ad sets. If it exceeds `targets.daily_budget_cap_usd * (1 - cap_headroom_pct/100)`, force `requires_approval: true` regardless of action.

## Step 6 — Plan executions

Sort decisions:
1. All `pause` actions first (stop bleeding).
2. All `scale_down` (trim noise).
3. `refresh_creative` / `launch_variant` (introduce new test).
4. `scale_up` last (commit capital only after cleanup).
5. Escalations → escalation queue (not executed).

## Step 7 — Execute auto-approved

For each auto-approved decision, call the appropriate Meta Ads MCP tool:
- `pause` → `mcp__meta-ads__update_adset` with `status=PAUSED`.
- `scale_up` / `scale_down` → `mcp__meta-ads__update_adset_budget`.
- `refresh_creative` → Read `data/creative-library.jsonl` for the next `status: "approved"` variant not yet deployed. If the library is empty or all variants are deployed, set `action=hold` and escalate with note: "Creative library exhausted — run `ad-creative` skill to generate new variants." Otherwise `mcp__meta-ads__create_ad_creative` + `update_ad` to rotate in the variant. Mark the used variant `status: "deployed"` in the library file.
- `launch_variant` → same as refresh but appends new ad instead of replacing.

After each execution:
- Append one line to `data/ad-history.jsonl`:
  ```json
  {"ts":"2026-04-21T10:02:14Z","mode":"full","adset_id":"...","action":"scale_up","from_usd":45,"to_usd":54,"hypothesis":"...","confidence":0.82,"revisit":"...","result":"ok"}
  ```
- If an execution fails, log `"result":"error", "error":"..."` and downgrade the decision to `requires_approval: true` in the briefing.

Then `git add data/ad-history.jsonl && git commit -m "ops: <date> <N decisions, $X spend, Y leads, Z hot>"`. **The commit is part of the contract** — it makes the decision history browsable later via `git log`.

## Step 8 — Morning briefing

Emit to stdout. Must be readable in ≤60 seconds. Lead with the number that matters most.

Format (literal template):

```
========================================
RE LEAD GEN — DAILY OPS BRIEFING
{date}  (mode: {mode})
========================================

HEADLINE
  Cost per lead: $X.XX   (target $Y.YY, last-7d avg $Z.ZZ)
  Qualified CPL: $X.XX   (target $Y.YY)
  Hot leads in last 24h: N
  Daily spend so far: $X (cap $Y)

HOT LEADS NEEDING CONTACT (SLA 2h)
  1. {name}, {interest}, score {s}  —  {segment}  —  {phone}  —  notes: {one-line}
  2. ...
  (if none) no hot leads pending contact

AUTO-EXECUTED TODAY ({n})
  - PAUSE {adset_name}  reason: frequency 3.4, ctr 0.006  conf 0.95
  - SCALE_UP {adset_name}  $45 → $54  conf 0.82
  - ...

ESCALATIONS NEEDING YOUR APPROVAL ({n})
  1. Expand audience on {adset_name} to include {location}. Hypothesis: ... Reply "approve 1" to execute.
  2. ...

FOLLOW-UPS DUE TODAY
  - Nurture sequence triggers: {n}
  - Drafts ready to review: python scripts/sheet-ops.py due

WATCHLIST (revisit triggers)
  - {adset_name}: watch CPL, revisit in 48h if > $40
  - ...

RECOMMENDED NEXT ACTION
  {one concrete thing}

========================================
```

## Guardrails (non-negotiable)

1. **Never exceed `daily_budget_cap_usd`.** Halt all scale_up actions if projected spend is within `cap_headroom_pct` of cap.
2. **Never scale an ad set with avg lead score <5.** Even if CPL is amazing — it's cheap junk.
3. **Never auto-approve `new_campaign` or `expand_audience`.**
4. **Every decision must have a hypothesis, confidence, and revisit_trigger.** A decision without them is malformed — fix it before executing.
5. **Git-commit or don't execute.** If you cannot git-commit (e.g., auth error, merge conflict), halt execution and escalate the full queue.
6. **Stale rules.** If `data/kill-scale-rules.json` or `data/scoring-model.json` has not been reviewed in 30+ days, add a briefing note recommending review (rules can rot).

## When things are ambiguous

Prefer `hold` over action. The default bias: do less, observe more. Three consecutive held days with the same observed pattern = escalate with a "should we change the rule?" note.

## Files this skill reads / writes

- **Reads:** `data/kill-scale-rules.json`, `data/scoring-model.json`, `data/property.json` (via property-context), `data/ad-history.jsonl` (last 50), `data/nurture-sequences.json`, `data/creative-library.jsonl`, Meta Ads MCP, `scripts/sheet-ops.py quality-by-adset`, `scripts/meta-insights.py`.
- **Writes:** `data/ad-history.jsonl` (append-only), git commits, stdout briefing.
