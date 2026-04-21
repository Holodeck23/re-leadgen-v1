# Setup Guide

## Prerequisites

- Google account (for Sheets + Apps Script)
- Meta Business account with ad access (for FB/IG ads)
- Pipeboard account (free, for Meta Ads MCP)
- Claude Code or Claude Pro/Max (for MCP + skills)
- Python 3.9+ with gspread (`pip install gspread`)

## Step 1: Google Sheet

1. Create a new Google Sheet
2. Add these headers in row 1:

```
timestamp | name | email | phone | interest | budget | timeline | message | source | score | status | notes | follow_up_date
```

3. Name the sheet "Leads" (or whatever you want, Sheet1 works)
4. Note the Sheet ID from the URL: `docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit`

## Step 2: Form Handler (Apps Script)

1. In the Google Sheet, go to Extensions > Apps Script
2. Replace the default code with the contents of `site/form-handler.gs`
3. Deploy > New Deployment
   - Type: Web App
   - Execute as: Me
   - Who has access: Anyone
4. Copy the deployment URL
5. Open `site/index.html` and replace `YOUR_GOOGLE_APPS_SCRIPT_URL` with that URL

## Step 3: Deploy Landing Page

Option A — Vercel (recommended):
```bash
cd site
npx vercel --prod
```

Option B — Netlify:
```bash
cd site
npx netlify deploy --prod --dir .
```

Option C — just open `index.html` in a browser for testing.

## Step 4: Google Sheets API (for Python scripts)

1. Go to Google Cloud Console > APIs & Services > Credentials
2. Create a Service Account
3. Download the JSON key file
4. Share the Google Sheet with the service account email (Editor access)
5. Set environment variables:

```bash
export GOOGLE_SHEETS_KEY_FILE="/path/to/your-key.json"
export LEAD_SHEET_ID="your-sheet-id-here"
```

6. Test:
```bash
pip install gspread
python scripts/sheet-ops.py all
```

## Step 5: Meta Ads MCP

### For Claude Code

Add to your Claude Code MCP config (`~/.claude/settings.json` or project `.mcp.json`):

```json
{
  "mcpServers": {
    "meta-ads": {
      "url": "https://mcp.pipeboard.co/meta-ads-mcp"
    }
  }
}
```

### For Claude.ai (Pro/Max)

1. Go to claude.ai/settings/integrations
2. Click "Add Integration"
3. Name: "Meta Ads"
4. URL: `https://mcp.pipeboard.co/meta-ads-mcp`
5. Connect and authenticate through Pipeboard

### Authentication

1. Create an account at pipeboard.co
2. Connect your Meta Business account
3. Get an API token at pipeboard.co/api-tokens
4. Use the token URL: `https://mcp.pipeboard.co/meta-ads-mcp?token=YOUR_TOKEN`

## Step 6: Install Skills in Claude Code

The skills in this project are designed to work from this project directory.
When you run Claude Code from `~/projects/re-leadgen-v1/`, the CLAUDE.md file
will load and the skills are accessible.

Usage:
```
# Generate ad copy
"Use the ad-copy skill to generate FB/IG ads for the 89-lot development"

# Score leads
"Run the lead scorer — here are the new leads: [paste CSV or use sheet-ops.py]"

# Draft follow-ups
"Use the follow-up skill to draft messages for all leads scored today"
```

## Daily Workflow

1. Check for new leads: `python scripts/sheet-ops.py new`
2. Score them with the lead-scorer agent
3. Draft follow-ups with the follow-up skill
4. Check ad performance via Meta Ads MCP: "Show me campaign performance for the last 7 days"
5. Generate fresh ad copy if CTR drops: use the ad-copy skill
6. Check for leads due follow-up: `python scripts/sheet-ops.py due`
