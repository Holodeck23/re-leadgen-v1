# Getting Started

_Last updated: 2026-04-24_

This system runs your Meta (Facebook + Instagram) ads, scores every lead automatically, drafts follow-up messages, and gives you a daily briefing. You handle sales calls and closing. The system handles everything else.

**Time to go live:** ~2 hours if your property content is ready. ~1 day if you're writing it from scratch.

## Fastest path: the setup wizard

```bash
./scripts/onboard.sh
```

This walks you through every step interactively — fills in your `.env`, creates the Google Sheet automatically, configures your landing page, and runs the preflight check at the end. If you get interrupted, run it again and it picks up where you left off.

If you prefer doing it manually, follow the steps below.

## What you need before starting

- A **Google account** (for the lead spreadsheet)
- A **Meta Business account** with ad access
- A **Pipeboard account** (free — https://pipeboard.co) for connecting Meta Ads
- **Claude Code** installed (`npm install -g @anthropic-ai/claude-code`, then `claude login`)
- **Python 3.10+** with pip
- Somewhere to host a static page (Vercel, Netlify, or GitHub Pages)

## Step 1: Clone and install

```bash
git clone <this-repo-url> re-leadgen-v1
cd re-leadgen-v1
git submodule update --init --recursive
pip install gspread requests
```

## Step 2: Fill in your property details

This is the most important step. Every ad, follow-up message, and landing page pulls from this one file.

```bash
cp data/property.example.json data/property.json
```

Open `data/property.json` and replace every field with your real property data. See `data/property.example.json` for what a completed file looks like.

**Required fields:**
- Project name, location (country, region, city, description)
- Inventory (lot count, sizes, price ranges)
- 3-5 concrete selling points (no filler — real facts with numbers)
- Target audiences (at least investors + homebuyers, with hooks and budget ranges)
- Amenities with distances
- Timeline (current phase, expected completion)
- Media URLs (photos, drone video, lot map, brochure)
- Sales contact (name, email, phone, WhatsApp)

**Check your work:**
```bash
python3 -c "import json; d=json.load(open('data/property.json')); assert 'UPDATE' not in json.dumps(d)"
```

## Step 3: Set up the lead spreadsheet

**Automatic (recommended):**
```bash
python scripts/create-sheet.py --email you@example.com
```
This creates a fully configured sheet with headers, column widths, data validation dropdowns (status, interest), conditional formatting (hot leads highlighted, duplicates greyed out), and shares it with your email. It prints the `LEAD_SHEET_ID` to add to your `.env`.

**Manual alternative:**
1. Create a new Google Sheet
2. Set Row 1 headers (exact order, lowercase):
   ```
   timestamp | name | email | phone | interest | budget | timeline | message | source | score | status | notes | follow_up_date
   ```
3. Google Cloud Console → create a service account → download the JSON key
4. Share the sheet with the service account email (Editor access)

## Step 4: Set up the form handler (Apps Script)

1. In the sheet: Extensions → Apps Script
2. Paste the contents of `site/form-handler.gs`
3. Set Script Properties:
   - `META_PIXEL_ID` — your Pixel ID from Meta Events Manager
   - `META_CAPI_TOKEN` — Conversions API token from Events Manager → Settings
   - `META_TEST_EVENT_CODE` — optional, for testing (remove after go-live)
4. Deploy → New deployment → Web app (Execute as: Me, Access: Anyone)
5. Copy the `/exec` URL

## Step 5: Configure the landing page

The landing page follows a visual design system defined in `site/DESIGN.md` — warm, trust-first, photography-forward. If your property has brand colors, set `branding.accent_color` in `data/property.json` to override the default earthy gold.

1. In `site/index.html` and `site/thank-you.html`:
   - Replace `REPLACE_WITH_DEPLOYED_APPS_SCRIPT_URL` with your Apps Script URL
   - Replace `PIXEL_ID` with your Meta Pixel ID
2. Deploy `site/` to your hosting provider:
   ```bash
   cp data/property.json site/property.json
   cd site && npx vercel --prod
   ```

## Step 6: Connect Meta Ads

1. Sign up at https://pipeboard.co and link your Meta ad account
2. Generate an API token
3. The `.mcp.json` file is already configured — just verify:
   ```bash
   claude
   > /mcp  # should show meta-ads connected
   ```

## Step 7: Set environment variables

Copy `.env.example` to `.env` and fill in the values:
```bash
cp .env.example .env
```

Required:
- `GOOGLE_SHEETS_KEY_FILE` — path to your service account JSON
- `LEAD_SHEET_ID` — from the Google Sheet URL
- `ANTHROPIC_API_KEY` — for the daily loop

## Step 8: Run the preflight check

```bash
./scripts/preflight.sh
```

Fix any failures, then run it again until everything passes.

## Step 9: Test the full loop

```bash
# Dry run — analyzes but doesn't execute any ad changes
./scripts/loop-runner.sh dry_run
```

Then submit a test form on your landing page and verify:
- Row appears in the sheet within 5 seconds
- `Lead` event appears in Meta Events Manager within 60 seconds
- Delete the test row when done

## Step 10: Launch your campaigns

**Recommended (zero ads experience needed):**

Open Claude Code in this project and say:
```
Launch my campaigns
```

The campaign launcher will:
1. Verify your property data and tracking are ready
2. Research the best audiences for your property
3. Generate professional ad creative with proven psychological hooks
4. Build your campaign structure (targeting, budgets, placements)
5. Walk you through everything and explain each decision
6. Create the campaigns in Meta — nothing goes live until you say "launch"

It handles Special Ad Category (Housing) compliance, learning-phase guardrails, and budget safety automatically.

**Manual alternative:**

If you prefer to create campaigns yourself in Meta Ads Manager:
1. Set Special Ad Category: Housing on every campaign
2. Set your ad URL parameters (every ad):
   ```
   adset_id={{adset.id}}&utm_source=facebook&utm_medium=paid&utm_campaign={{campaign.name}}&utm_content={{ad.name}}
   ```
3. Launch 1-3 campaigns at $20-50/day per ad set

**After launching (either method), install the daily loop:**
```bash
# Add to crontab (adjust path and timezone):
0 8 * * *              cd /path/to/re-leadgen-v1 && ./scripts/loop-runner.sh >> ops.log 2>&1
0 9,11,13,15,17,19 * * * cd /path/to/re-leadgen-v1 && ./scripts/loop-runner.sh hot_sweep >> ops.log 2>&1
```

## After go-live: your daily routine

**Morning (2 minutes):** Read the briefing. Contact any hot leads within 2 hours. Approve or reject escalations.

**Friday (30 minutes):** Review the week's ad decisions. Check lead quality trends. Tune thresholds in `data/kill-scale-rules.json` if something looks off.

**When you close a deal:** Tag the row in the sheet as `closed`. The system uses this to improve over time.

## Important: first 2 weeks (the learning phase)

Meta's algorithm needs about 14 days and 50 Lead events to learn who your best buyers are. During this window:

- **Don't change audiences or targeting** — it resets the learning phase
- **Don't change budgets by more than 20%** — same reason
- **Don't rotate creative** unless something is clearly failing (the system knows when)
- **Do** let the system pause underperformers — that's safe and saves budget

The system tracks learning-phase status automatically in `data/launch-config.json` and restricts its own actions during this window. If you used the campaign launcher, it set up a hybrid approach: 60% manual targeting (so you can see which segments work) + 40% Advantage+ (so Meta can find buyers you didn't expect). Once you hit 50 events, Advantage+ improves dramatically.

## If something breaks

- Run `./scripts/preflight.sh` to check your setup
- Read `docs/runbook.md` for common issues and fixes
- Emergency: `./scripts/loop-runner.sh emergency_brake` pauses all ads immediately

## Reference docs

| Doc | When to read |
|-----|-------------|
| `docs/walkthrough.md` | Once — full system tour (15 min) |
| `docs/runbook.md` | When something needs attention |
| `docs/setup.md` | Detailed setup reference |
