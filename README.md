# RE Lead Gen V1

An autonomous Meta-ads + lead-qualification system for real estate, powered by Claude Code. One person plus a daily loop replaces a media buyer, marketing coordinator, and BDR.

Works for any property listing. Swap `data/property.json`, refresh the Meta pixel, go.

## What it does

- Launches campaigns from scratch — zero ads experience required (audience research, creative generation, campaign structure, go-live)
- Runs a daily reflective loop: analyze ad performance, score leads, auto-execute safe actions, escalate the rest
- Scores leads on a 0-100 BANT + behavioral + property-fit rubric with two-phase tiering (initial intent-based SLA, post-contact full rubric)
- Drafts segment-aware follow-ups (WhatsApp-first for hot leads, email for artefacts)
- Runs milestone-triggered nurture sequences (not calendar drip)
- Manages Meta campaigns with published kill/scale thresholds and a lead-quality gate
- Identifies organic unicorn posts for paid promotion ($50 auditions)
- Logs every decision to `data/ad-history.jsonl` + git commits for full audit trail

## Architecture

```
[FB/IG Ads] → [Landing Page] → [Google Sheet (CRM)]
                                       │
                               [Claude Code + cron]
                              /        │        \
                       Score leads   Draft     Monitor + optimize
                       (0-100)     follow-ups  campaigns (Meta MCP)
```

No app to deploy, no server to maintain, no database to migrate. The stack: a static site, a spreadsheet, a Meta ad account, markdown skills that tell Claude how to behave, and a shell script on cron.

## Quick start

```bash
git clone <this-repo-url> re-leadgen-v1
cd re-leadgen-v1
git submodule update --init --recursive
./scripts/onboard.sh
```

The onboarding wizard walks you through everything: property details, Google Sheets, Apps Script, Meta Pixel, environment variables. It creates your CRM sheet automatically and validates every step.

Or do it manually: `docs/HANDOFF.md` has the full 10-step guide. `docs/walkthrough.md` has the architecture tour.

## Project structure

```
.
├── CLAUDE.md                        # Operating rules for Claude
├── .mcp.json                        # Meta Ads MCP config (Pipeboard)
├── data/
│   ├── property.example.json        # Example listing (copy to property.json during setup)
│   ├── property.json                # Your listing details — created during onboarding
│   ├── scoring-model.json           # BANT + behavioral scoring rubric
│   ├── kill-scale-rules.json        # Pause/scale/refresh thresholds + learning phase
│   ├── launch-config.json           # Created at launch — campaigns + learning phase state
│   ├── nurture-sequences.json       # Milestone-triggered nurture sequences
│   ├── creative-library.jsonl       # Pre-approved ad variants
│   └── ad-history.jsonl             # Append-only decision log
├── skills/
│   ├── campaign-launch/             # Zero-to-live: 9-step campaign creation
│   ├── audience-research/           # Build targeting from property data
│   ├── reflective-ops/              # Daily analyze → iterate → execute loop
│   ├── lead-qualifier/              # Score leads 0-100, assign tier + segment
│   ├── follow-up/                   # Draft WhatsApp + email by segment
│   ├── nurture-orchestrator/        # Advance leads through sequences
│   ├── property-context/            # Load property.json + anti-slop rules
│   ├── ad-creative/                 # Generate Meta ad variants (6 hook types)
│   ├── competitive-intel/           # Analyze competitor ads → inspiration seeds
│   ├── paid-ads/                    # Campaign lifecycle (Meta-only, Housing)
│   ├── ads-meta/                    # Creative fatigue + Pixel health audit
│   ├── unicorn-promoter/            # Promote organic outliers
│   ├── analytics-tracking/          # Pixel + CAPI + UTM instrumentation
│   ├── ab-test-setup/               # Hypothesis-driven A/B tests
│   ├── page-cro/                    # Landing page optimization
│   ├── form-cro/                    # Form optimization
│   └── ads-generate/                # Image generation
├── agents/
│   ├── campaign-launcher.md         # Zero-to-live campaign agent (sonnet)
│   ├── reflective-operator.md       # Daily loop agent (sonnet)
│   ├── lead-scorer.md               # Batch scoring agent (haiku)
│   └── creative-auditor.md          # On-demand creative audit (sonnet)
├── scripts/
│   ├── onboard.sh                   # Interactive setup wizard
│   ├── preflight.sh                 # Pre-launch validation
│   ├── create-sheet.py              # Auto-create configured CRM sheet
│   ├── loop-runner.sh               # Cron entrypoint
│   ├── sheet-ops.py                 # Google Sheets CLI
│   └── meta-insights.py             # Meta Graph API fallback
├── site/
│   ├── DESIGN.md                    # Visual design system (colors, typography, components)
│   ├── index.html                   # Landing page (3-field form + Pixel)
│   ├── form-handler.gs              # Apps Script (form → Sheet + CAPI)
│   └── thank-you.html               # Post-submit (Calendly + email capture)
├── docs/
│   ├── HANDOFF.md                   # Cold-start entry point
│   ├── walkthrough.md               # Full system tour
│   ├── runbook.md                   # Operational guide
│   └── setup.md                     # Installation steps
├── vendor/                          # Pinned submodules (reference only)
└── tests/fixtures/                  # Dry-run test payloads
```

## Daily workflow

1. Morning briefing (cron output) — hot leads first, then escalations, then metrics
2. Contact hot leads within 2h (WhatsApp-first)
3. Approve or reject escalations
4. Friday 30min: review the week's decisions, tune thresholds if needed

## Key guardrails

- **Lead-quality gate**: never scales an ad set whose 14-day avg lead score is below threshold
- **Daily budget cap**: hard stop, enforced at preflight
- **Approval gates**: new campaigns, audience expansion, targeting changes always escalate
- **Learning-phase protection**: first 14 days / 50 Lead events — restricts to pause/hold only so Meta's algorithm can optimize
- **Housing compliance**: Special Ad Category enforced on every campaign (ages 18–65+, all genders, no ZIP, 15-mile min radius)

## Security & Safety

- **RCE Mitigation**: AI agents are restricted from arbitrary shell execution (`Bash` tool removed for scoring/auditing agents).
- **Prompt Injection Defense**: Lead data is strictly encapsulated in XML tags; models are instructed to treat it as inert text.
- **Data Poisoning Defense**: Suspicious lead spikes (>50/day per ad set) or sudden quality drops automatically disable auto-scaling and force human review.
- **Audit Trail**: Every decision is git-committed with a rationale, providing a non-repudiable history of autonomous actions.

## Requirements

- Claude Code (authenticated)
- Python 3.10+
- Google account (Sheets + Apps Script)
- Meta Business account with ad access
- Pipeboard account (free, for Meta Ads MCP)

## Docs

| Doc | When to read |
|-----|-------------|
| `docs/HANDOFF.md` | First — cold-start entry point (5 min) |
| `docs/walkthrough.md` | Once — full system tour (15 min) |
| `docs/runbook.md` | Before acting on escalations (10 min) |
| `docs/setup.md` | When installing (20 min) |

## Customizing for other properties

1. Update `data/property.json`
2. Refresh the Meta Pixel ID in `site/` files
3. Open Claude Code and say "Launch my campaigns" — the campaign launcher handles audience research, creative generation, campaign structure, and go-live
4. Everything else adapts — skills read from property.json
