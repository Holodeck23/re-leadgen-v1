# Setup Guide

Bring this system online end-to-end. Work through the sections in order — each one unblocks the next. Budget ~2 hours the first time.

## 0. Prerequisites

- Google account (for Sheets + Apps Script)
- Meta Business account with ad access (Business Manager + an ad account)
- Pipeboard account — https://pipeboard.co/api-tokens (free tier, for the Meta Ads MCP)
- Claude Code installed and authenticated (`claude login`)
- Python 3.10+
- A hosting target for the static landing page (Vercel / Netlify / GitHub Pages)

## 1. Clone + initialise submodules

```bash
git clone <this-repo> re-leadgen-v1
cd re-leadgen-v1
git submodule update --init --recursive
git submodule status   # should show vendor/claude-ads and vendor/marketingskills at pinned SHAs
```

The two vendored repos live under `vendor/` as reference. The active copies (patched with RE context) live in `skills/`. Don't edit `vendor/`.

## 2. Populate `data/property.json`

This file is the single source of truth for every ad, follow-up, and landing-page fact. The system refuses to run until every `UPDATE` placeholder is replaced with real content.

```bash
# Sanity check — must pass before go-live
python3 -c "import json; d=json.load(open('data/property.json')); assert 'UPDATE' not in json.dumps(d), 'property.json still has UPDATE placeholders'"
```

```bash
cp data/property.example.json data/property.json
```

Required fields (see `data/property.example.json` for a completed example):
- `project_name`, `location.{country,region,city,description}`
- `inventory.lots.{total,available,size_range,price_range}`
- `inventory.complex_units.{total,available,types,price_range}`
- `key_selling_points` (3–5 concrete points, no filler)
- `target_audiences` (at least: investors, homebuyers)
- `amenities` (real nearby features with distances if possible)
- `timeline.{phase_1,completion}`
- `media.{photos,drone_video,lot_map,brochure}` — URLs to hosted assets
- `contact.{sales_name,sales_email,sales_phone,sales_whatsapp}` — `sales_whatsapp` as digits only (no `+`, no spaces)

## 3. Google Sheet + service account

1. Create a Google Sheet. Row 1 headers (exact order, lowercase):
   ```
   timestamp | name | email | phone | interest | budget | timeline | message | source | score | status | notes | follow_up_date
   ```
2. Google Cloud Console → create a service account → generate a JSON key → download it.
3. Share the sheet with the service-account email (Editor access).
4. Save credentials:
   ```bash
   export GOOGLE_SHEETS_KEY_FILE=/absolute/path/to/service-account.json
   export LEAD_SHEET_ID=...   # from the sheet URL
   ```
5. Smoke test:
   ```bash
   pip install gspread
   python scripts/sheet-ops.py all
   ```

## 4. Apps Script form handler

1. In the sheet: Extensions → Apps Script.
2. Paste the contents of `site/form-handler.gs`.
3. File → Project properties → Script properties. Set:
   - `META_PIXEL_ID` — numeric Pixel ID. Required to fire server-side CAPI events.
   - `META_CAPI_TOKEN` — Conversions API access token from Events Manager → Settings → Conversions API.
   - `META_TEST_EVENT_CODE` — optional. When set, events flow into the Test Events panel instead of production; clear it after go-live.
   - `HOT_LEAD_WEBHOOK_URL` — optional. Endpoint that receives instant hot-lead notifications (see §8).
   - `HOT_LEAD_WEBHOOK_TOKEN` — optional Bearer token for the hot-lead webhook.

   Without `META_PIXEL_ID` + `META_CAPI_TOKEN`, the Apps Script still writes rows to the sheet but server-side `Lead` and `CompleteRegistration` events are skipped silently — EMQ drops and iOS 14.5+ attribution regresses to client-only. Set both before driving paid traffic.
4. Deploy → New deployment → Web app:
   - Execute as: Me
   - Who has access: Anyone
5. Copy the `/exec` URL. In `site/index.html` and `site/thank-you.html` replace `REPLACE_WITH_DEPLOYED_APPS_SCRIPT_URL` with it.

## 5. Meta Pixel + CAPI

1. Meta Events Manager → create a Pixel. Copy the Pixel ID.
2. In `site/index.html` and `site/thank-you.html` replace both `PIXEL_ID` strings.
3. Events Manager → Settings → Conversions API → Generate Access Token. Paste it into the `META_CAPI_TOKEN` Script Property in §4. The Apps Script sends a server-side `Lead` event on submit and `CompleteRegistration` on thank-you-page email capture, both sharing the `event_id` with the client-side Pixel for dedup.
4. Test: submit the landing form, confirm a `Lead` event in Events Manager within a minute, with the same `event_id` as the redirect URL and dedup from the client-side Pixel. EMQ should land ≥8 with phone + external_id + user_agent hashed. Capture an email on the thank-you page and confirm `CompleteRegistration` fires with the same `event_id`.

### 5.1 Ad URL parameters — attribution that survives renames

In Ads Manager → Ad → URL parameters, add:

```
adset_id={{adset.id}}&utm_source=facebook&utm_medium=paid&utm_campaign={{campaign.name}}&utm_content={{ad.name}}
```

`adset_id={{adset.id}}` is the canonical join key. The UTM string is the fallback for organic/referral traffic. `scripts/sheet-ops.py quality-by-adset` reads `adset_id` from the notes column first and only parses UTMs when it's absent, so renaming a campaign or ad in Meta does not break the lead-quality gate.

## 6. Meta Ads MCP (Pipeboard)

1. https://pipeboard.co → sign up → link your Meta ad account → generate an API token.
2. `.mcp.json` is preconfigured for the Pipeboard remote MCP. First run:
   ```bash
   claude
   > /mcp  # verify meta-ads server shows connected
   ```
3. If auth fails, refresh the token at https://pipeboard.co/api-tokens.

## 7. Local env for the cron loop

Add to `.env` or your shell profile:

```bash
export GOOGLE_SHEETS_KEY_FILE=/abs/path/to/service-account.json
export LEAD_SHEET_ID=...
export META_ACCESS_TOKEN=...          # only needed for scripts/meta-insights.py fallback
export META_AD_ACCOUNT_ID=act_1234567890
export ANTHROPIC_API_KEY=sk-ant-...   # for `claude` headless in loop-runner.sh
```

Smoke tests:

```bash
python scripts/sheet-ops.py new                        # should print []
python scripts/sheet-ops.py quality-by-adset           # should print {"by_adset":[...]}
python scripts/meta-insights.py | jq '.adsets|length'  # sanity for Meta credentials
```

## 8. Deploy the landing page

The landing page follows a visual design system defined in `site/DESIGN.md` — warm off-white palette, earthy gold accent, system fonts, photography-forward. If your property has brand colors, set `branding.accent_color` in `data/property.json` to override the default accent. The `page-cro` skill reads `DESIGN.md` before making any markup or style changes.

Any static host works. The page fetches `./property.json` at runtime, so deploy `site/` alongside a copy of `data/property.json`:

```bash
cp data/property.json site/property.json
cd site && npx vercel --prod
```

For Netlify or GitHub Pages, publish the `site/` directory. Wire a custom domain, then plug it into the Pixel setup so event-match quality scores lift.

## 9. Schedule the reflective-ops loop

The loop has two cadences:

- **Full daily run** (heavy; analyze + iterate + execute) — once a day.
- **Hot-lead sweep** (light; scan for new leads + alert) — every 2 hours 08:00–20:00.

Install via crontab (example, local time; adjust path):

```cron
0 8 * * *                    cd /path/to/re-leadgen-v1 && ./scripts/loop-runner.sh             >> ops.log 2>&1
0 9,11,13,15,17,19 * * *     cd /path/to/re-leadgen-v1 && ./scripts/loop-runner.sh hot_sweep   >> ops.log 2>&1
```

Or use the `scheduled-tasks` MCP:

```
claude > use scheduled-tasks to create a daily task at 08:00 running /abs/path/re-leadgen-v1/scripts/loop-runner.sh
```

First invocation exits loudly if any of the property.json / env / MCP / Pixel prerequisites are missing. Fix each one and re-run.

## 10. Launch campaigns

**Recommended (zero ads experience needed):**

Open Claude Code in this project and say "Launch my campaigns." The campaign launcher agent will:
1. Verify property data and tracking are ready
2. Research the best audiences for your property (Housing-compliant)
3. Generate ad creative with proven psychological hooks
4. Build campaign structure (budgets, placements, targeting)
5. Walk you through every decision — nothing goes live without your approval
6. Set up learning-phase guardrails (14 days / 50 events)

**Manual alternative:** Create campaigns yourself in Meta Ads Manager. Set Special Ad Category: Housing on every campaign. Use the URL parameters from §5.1.

## 11. First-run checklist

Before driving any traffic:

- [ ] `git submodule status` shows both vendored repos at pinned SHAs.
- [ ] `python3 -c "import json; d=json.load(open('data/property.json')); assert 'UPDATE' not in json.dumps(d)"` passes.
- [ ] Landing form submit lands a row in the sheet within 5 seconds.
- [ ] Meta Events Manager shows the `Lead` event with matching `event_id` and EMQ ≥ 7.
- [ ] `python scripts/sheet-ops.py new` returns the test row.
- [ ] `python scripts/sheet-ops.py quality-by-adset --window-days 14` runs without error.
- [ ] `claude > /mcp` shows `meta-ads` connected.
- [ ] `scripts/loop-runner.sh dry_run` completes and prints a briefing to stdout.
- [ ] One real daily run committed to `data/ad-history.jsonl` with a git commit (`ops: <date> …`).

When every box is ticked, turn on ads.

## Troubleshooting quick-reference

| Symptom | Fix |
| --- | --- |
| `property.json placeholder` error at run | Replace all `UPDATE` strings in `data/property.json` |
| `gspread.exceptions.APIError: 403` | Re-share the sheet with the service-account email |
| Apps Script form returns 500 | Open Apps Script → View → Executions; usually a header order mismatch |
| Pixel `Lead` not firing | Pixel ID still placeholder; confirm `fbq('init', '…')` has the real ID |
| `claude: command not found` in cron | Use the absolute path to `claude` in `loop-runner.sh` |
| `meta-ads` MCP not connected | Refresh token at pipeboard.co/api-tokens |
| Loop refuses to scale a cheap ad set | Lead-quality gate blocked it — by design; see `docs/runbook.md` |
