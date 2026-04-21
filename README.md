# RE Lead Gen V1

A Claude Code-powered lead generation system for real estate. Built for a live deal (89 lots + complex), designed to be reusable for any property listing.

## What It Does

- Generates Facebook and Instagram ad copy tailored to different buyer segments
- Manages ad campaigns directly through Meta Ads MCP (create, monitor, optimize, A/B test)
- Captures leads via a landing page into Google Sheets
- Scores and qualifies leads automatically
- Drafts personalized follow-up emails and WhatsApp messages
- Runs nurture sequences based on lead temperature
- Gives you a daily briefing: new leads, ad performance, pipeline health, what to do next

## How It Works

The system runs inside Claude Code. You open this project directory and talk to Claude. Claude has skills for each part of the operation, an MCP connection to Meta Ads, and a Python helper for the Google Sheets CRM.

There is no separate app to deploy or maintain. Claude IS the app.

```
[FB/IG Ads] → [Landing Page] → [Google Sheets]
                                      |
                              [Claude Code]
                             /      |       \
                      Score leads  Draft     Monitor
                      (1-10)     follow-ups  campaigns
```

## Quick Start

1. Fill in `data/property.json` with real listing details
2. Set up the Google Sheet and Apps Script (see `docs/setup.md`)
3. Deploy `site/index.html` to Vercel/Netlify/Railway
4. Connect Meta Ads MCP via Pipeboard (config already in `.mcp.json`)
5. Open Claude Code in this directory and say "morning briefing"

Full setup instructions in `docs/setup.md`.

## Project Structure

```
.
├── CLAUDE.md                    # Claude Code project instructions
├── .mcp.json                    # Meta Ads MCP server config
├── data/
│   ├── property.json            # Listing details (fill this in first)
│   └── nurture-sequences.json   # Drip sequence definitions by lead tier
├── site/
│   ├── index.html               # Landing page with lead capture form
│   └── form-handler.gs          # Google Apps Script (form → Sheets)
├── skills/
│   ├── ad-copy/SKILL.md         # Generate FB/IG ad variations
│   ├── lead-qualifier/SKILL.md  # Score leads 1-10
│   ├── follow-up/SKILL.md       # Draft follow-up messages
│   ├── campaign-ops/SKILL.md    # Campaign lifecycle management
│   └── daily-ops/SKILL.md       # Morning briefing
├── agents/
│   └── lead-scorer.md           # Batch lead scoring agent
├── scripts/
│   └── sheet-ops.py             # Google Sheets read/write CLI
└── docs/
    └── setup.md                 # Full setup guide
```

## Daily Workflow

1. "Morning briefing" — pulls new leads, ad performance, pipeline status
2. Score any new leads — Claude flags hot ones for immediate contact
3. Draft follow-ups — personalized by lead tier and sequence step
4. Check ads — Claude reports CPL, CTR, flags fatigue or budget issues
5. Optimize — pause losers, refresh creative, scale winners

## Requirements

- Claude Code (or Claude Pro/Max for MCP)
- Google account (Sheets + Apps Script)
- Meta Business account with ad access
- Pipeboard account (free, pipeboard.co)
- Python 3.9+ with gspread

## Customizing for Other Properties

1. Update `data/property.json` with the new listing
2. Update `site/index.html` copy (hero, features, form options)
3. Adjust budget ranges in the lead qualifier skill if price points differ
4. Everything else adapts automatically — skills read from property.json
