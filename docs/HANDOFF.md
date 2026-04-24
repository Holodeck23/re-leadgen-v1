# Handoff — re-leadgen-v1

_Last updated: 2026-04-24_

If you just opened this repo (human or fresh Claude session), read this first. It tells you what's built, what's broken, what to do next, and in what order.

For the full tour, read `docs/walkthrough.md` once. For day-to-day ops, read `docs/runbook.md` before acting on any escalation. This file is the punch list.

## What's on `main`

Commit `2a3819a`: a daily autonomous Meta-ads + AI-lead-qualification loop.

- Reflective-ops loop (analyze → iterate → execute) with lead-quality as the gating signal.
- 14 skills: 6 patched from `marketingskills`, 2 from `claude-ads`, 6 written for this repo (`reflective-ops`, `lead-qualifier`, `follow-up`, `nurture-orchestrator`, `unicorn-promoter`, `property-context`).
- 3 agents: `reflective-operator` (sonnet, daily loop), `lead-scorer` (haiku, batch), `creative-auditor` (sonnet, on-demand).
- Landing page with Pixel + server-side CAPI (Lead + CompleteRegistration, hashed PII, event_id dedup). 3-field form. Thank-you page with progressive email + Calendly for hot interest.
- Attribution: `adset_id={{adset.id}}` Meta URL macro captured end-to-end, survives campaign renames. UTM is fallback only.
- Single sources of truth under `data/`: `property.json`, `scoring-model.json`, `kill-scale-rules.json`, `nurture-sequences.json`, `ad-history.jsonl`.

## What's NOT done — go-live blockers

Cannot drive a single paid click until all four are green.

### 1. Populate `data/property.json` (hard blocker)

Every `"UPDATE"` string must be replaced with real content. `property-context` returns `BLOCKED` otherwise, and every downstream skill halts.

```bash
# Verify:
python3 -c "import json; d=json.load(open('data/property.json')); assert 'UPDATE' not in json.dumps(d)"
```

Minimum fields required before the sanity check passes: see `docs/setup.md` §2.

### 2. ~~Fix two-phase lead scoring~~ DONE

**Fixed (Strategy B).** `scoring-model.json` now has `initial_phase` config. `lead-qualifier` SKILL.md updated to read `phase: initial | post_contact`. Initial-phase leads get tier overrides based on intent keywords + phone presence (hot = "contact within 2h"), while the full-rubric score is still computed and stored for the quality gate. Post-contact rescoring uses the full BANT rubric.

### 3. Seed the creative variant library (scaffolded, needs content)

`data/creative-library.jsonl` now exists (empty). `reflective-ops` and `paid-ads` SKILLs updated to read it, handle the empty case (escalate instead of crash), and mark variants as deployed after use.

**Still needed:** populate with 6 approved variants once `data/property.json` has real content. Run:
```bash
claude > /skill ad-creative
# Review outputs for anti-slop (no "nestled in", "boasts", etc.)
# Each line in data/creative-library.jsonl:
# {"id":"v01","format":"feed","segment":"investor","headline":"…","primary_text":"…","image_ref":"…","status":"approved"}
```

### 4. Verify headless MCP + CAPI before cron

Two unverified integrations. Either can silently fail from cron.

**4a. Pipeboard MCP in non-interactive Claude.** The daily loop is `scripts/loop-runner.sh` → `claude --print --agent reflective-operator`. MCP auth behavior in headless `--print` mode isn't confirmed. Smoke test:
```bash
./scripts/loop-runner.sh dry_run 2>&1 | tee /tmp/dryrun.log
grep -E "(ERROR|BLOCKED|auth)" /tmp/dryrun.log  # must be empty
```
If MCP doesn't connect, `scripts/meta-insights.py` is the fallback — but that requires `META_ACCESS_TOKEN` (Meta Graph, not Pipeboard). Set both in env.

**4b. CAPI event landing.** Submit one real form against the deployed Apps Script endpoint.
- Meta Events Manager → Test Events panel → confirm `Lead` event arrives within 60s.
- `event_id` must dedup with the client-side Pixel event (appears as single event, not two).
- EMQ must land ≥ 8 (phone + external_id + user_agent + action_source=website).
- If EMQ < 8: re-check SHA-256 hashing (trim + lowercase before hashing), confirm `META_PIXEL_ID` and `META_CAPI_TOKEN` Script Properties are set (see `docs/setup.md` §4).

## What's missing but not blocking launch

Do these in weeks 2–4, after you have real data to work against.

### Deal-outcome pipeline (for eventual scoring-model tuning)

Sheet has `status=closed` as a value; nothing reads it. Scoring weights cannot improve over time until they can be correlated with real closes.

**Minimum viable (30 min):**
- `scripts/close-deal.py <row> --value <usd> --notes "..."` sets `status=closed`, appends to `data/closed-deals.jsonl`.
- No retraining yet — just start collecting the truth set. Do NOT auto-tune weights on fewer than 30 closed deals; live updating on small samples is noise amplification.
- Monthly manual review: compute score-vs-close correlation on closed deals; if a feature weight is systematically misaligned, edit `scoring-model.json` deliberately.

### Milestone event input (for nurture-orchestrator)

`nurture-orchestrator` fires on milestones like `new_drone_footage_published`, `lot_sold_in_same_phase`, `price_change_announced`. There's no input path documented. Currently every "milestone-triggered" step is actually a calendar-fallback step.

**Fix (2 h):**
- `scripts/milestone.py add <type> [--notes "..."]` appends to `data/milestones.jsonl`.
- `nurture-orchestrator` reads that file at run time; clears entries after they've fired once.

### First-launch targeting override

`paid-ads` SKILL says "start with Advantage+ audience." Advantage+ needs ~50 conversion events to converge. First 2 weeks with zero conversion history = Meta fires broad = lead-quality gate holds everything = the loop looks broken. Add to `docs/runbook.md`:

> **First 2 weeks / first 50 conversion events:** do not use Advantage+ audience. Use interest + location constrained targeting (country + real-estate / investment interests + age 25–65). Switch to Advantage+ only after Meta has enough signal.

### WhatsApp send integration

`follow-up` drafts; nothing actually sends. The 2h hot-lead SLA is human-enforced. Fine for v1. When volume justifies it, integrate the WhatsApp Business API or a 3rd-party (Twilio for WhatsApp, Messagebird) — and keep the draft-approve-send gate for the first 30 days.

### Real tests + CI

`tests/fixtures/*` exists; there's no pytest suite or CI. Phase-6 verification was ad-hoc. Before v2, wire the fixtures into pytest and add a simple GitHub Actions workflow that runs on PRs.

## First-day runbook (when you're ready to turn traffic on)

1. Populate `data/property.json`. Run the placeholder-check. Commit.
2. Fix two-phase scoring (pick strategy B above). Commit.
3. Seed `data/creative-library.jsonl` with 6 approved variants. Commit.
4. Set env vars (see `docs/setup.md` §7). Confirm `python scripts/sheet-ops.py new` returns `[]`.
5. Set Apps Script Properties (`META_PIXEL_ID`, `META_CAPI_TOKEN`, optional `META_TEST_EVENT_CODE`, optional `HOT_LEAD_WEBHOOK_URL` + token). Redeploy the Web app.
6. In Meta Ads Manager → every Ad → URL parameters:
   ```
   adset_id={{adset.id}}&utm_source=facebook&utm_medium=paid&utm_campaign={{campaign.name}}&utm_content={{ad.name}}
   ```
7. Run `scripts/loop-runner.sh dry_run`. Resolve any error before cron.
8. Submit a real form. Verify: row in sheet in ≤5s, `Lead` event in Events Manager with EMQ ≥ 8, `event_id` dedup clean. Delete the test row.
9. Install cron (see `docs/setup.md` §8). First daily run should commit `ops: YYYY-MM-DD …` automatically.
10. Launch 1–3 campaigns at small daily budget ($20–50/ad set). Watch the first briefing. Adjust thresholds in `kill-scale-rules.json` only after ≥50 real leads.

## Weekly / monthly cadence

- **Friday 30 min:** `docs/runbook.md` → "Weekly review cadence."
- **First-of-month 60 min:** `docs/runbook.md` → "Monthly review."
- **Whenever you close a deal:** run the deal-outcome script (once built). Weekly, skim the score-vs-close pattern; don't retune until ≥30 closes.

## Known speculative pieces

Call these out because a fresh operator should know they're priors, not calibrations:

- `scoring-model.json` weights: reasonable priors. Never tuned against real closes.
- `kill-scale-rules.json` thresholds: industry-defensible, not account-specific.
- `tiers.hot.min = 70`: a guess. Will need to move after 50+ real leads.
- `min_avg_lead_score_for_scale_up = 5.0` (on 1–10 scale): a guess.
- `audience_segments`: signal lists are a priori word-match. Will need refinement from real lead messages.
- `nurture-sequences.json` max_wait_days / hours: guesses. Tune from reply-rate data.
- Creative variant counts (6 per refresh): a guess. Probably fine.

Nothing in this file is load-bearing forever. The point of the repo is that the audit trail (`data/ad-history.jsonl` + git commits) lets you see what was decided and why, and refine.

## Contacts / where the bodies are buried

- `vendor/claude-ads` pinned at `402ba63` (public OSS).
- `vendor/marketingskills` pinned at `9125d82` (public OSS).
- The RE-patched copies under `skills/` deliberately diverge — upstream bumps are a quarterly review task, not a blind pull.
- The previous weak skills live under `skills-deprecated/` — kept for rationale, not invoked.
- The worktree used during rebuild (`claude/funny-pike-e8a14e`) has been merged and removed.

## If you inherit this cold

Order of reads:
1. `docs/HANDOFF.md` (this file) — 5 min
2. `docs/walkthrough.md` — 15 min, the big-picture tour
3. `CLAUDE.md` — 5 min, the operating rules
4. `data/property.json` — 5 min (or however long it takes to populate)
5. `docs/runbook.md` — 10 min, bookmark for later
6. `docs/setup.md` — 20 min when you're installing

Total cold-start to first-form-submit: ~2 hours if property.json content is ready; ~1 day if you're writing the property copy from scratch.
