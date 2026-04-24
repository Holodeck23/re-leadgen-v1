#!/usr/bin/env bash
# Interactive onboarding wizard for re-leadgen-v1.
# Walks a new user through every setup step, validates as they go,
# and creates resources (sheet, env file) automatically where possible.
#
# Usage: ./scripts/onboard.sh

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# --- helpers ---

BOLD="\033[1m"
DIM="\033[2m"
GREEN="\033[32m"
YELLOW="\033[33m"
RED="\033[31m"
CYAN="\033[36m"
RESET="\033[0m"

step_num=0
step() {
  step_num=$((step_num + 1))
  echo ""
  echo -e "${BOLD}${CYAN}[$step_num] $1${RESET}"
  echo ""
}

ok()   { echo -e "  ${GREEN}✓${RESET} $1"; }
skip() { echo -e "  ${DIM}→ $1${RESET}"; }
err()  { echo -e "  ${RED}✗${RESET} $1"; }
warn() { echo -e "  ${YELLOW}~${RESET} $1"; }
info() { echo -e "  $1"; }

ask() {
  local prompt=$1
  local var_name=$2
  local default=${3:-}
  if [[ -n "$default" ]]; then
    echo -en "  ${prompt} [${default}]: "
  else
    echo -en "  ${prompt}: "
  fi
  read -r input
  if [[ -z "$input" ]] && [[ -n "$default" ]]; then
    input="$default"
  fi
  eval "$var_name='$input'"
}

ask_yn() {
  local prompt=$1
  local default=${2:-y}
  echo -en "  ${prompt} [${default}]: "
  read -r input
  input="${input:-$default}"
  [[ "$input" =~ ^[Yy] ]]
}

wait_for_enter() {
  echo ""
  echo -en "  ${DIM}Press Enter when done...${RESET}"
  read -r
}

# --- start ---

echo ""
echo -e "${BOLD}======================================${RESET}"
echo -e "${BOLD}  RE LEAD GEN — SETUP WIZARD${RESET}"
echo -e "${BOLD}======================================${RESET}"
echo ""
echo "  This will walk you through connecting everything."
echo "  Takes about 30 minutes. You can quit anytime and"
echo "  pick up where you left off — run this script again"
echo "  and it'll skip steps that are already done."
echo ""

# ============================================================
step "Python dependencies"
# ============================================================

missing_deps=()
if ! python3 -c "import gspread" 2>/dev/null; then
  missing_deps+=("gspread")
fi
if ! python3 -c "import requests" 2>/dev/null; then
  missing_deps+=("requests")
fi

if [[ ${#missing_deps[@]} -eq 0 ]]; then
  ok "gspread and requests already installed"
else
  info "Installing: ${missing_deps[*]}"
  pip install "${missing_deps[@]}" --quiet
  ok "Dependencies installed"
fi

# ============================================================
step "Property details"
# ============================================================

if [[ -f data/property.json ]] && ! grep -q '"UPDATE' data/property.json; then
  ok "data/property.json already populated"
else
  if [[ ! -f data/property.json ]]; then
    cp data/property.example.json data/property.json
    info "Created data/property.json from the example file."
  fi

  count=$(grep -c '"UPDATE' data/property.json 2>/dev/null || echo "0")
  warn "data/property.json has ${count} fields still set to UPDATE."
  echo ""
  info "Open this file and fill in your property details:"
  echo ""
  echo -e "    ${BOLD}data/property.json${RESET}"
  echo ""
  info "Reference: data/property.example.json shows a completed example."
  echo ""
  info "Key fields: project name, location, inventory (lots + units),"
  info "price ranges, selling points, target audiences, amenities,"
  info "timeline, media URLs, and your sales contact."

  if ask_yn "Open property.json in your editor now? (y/n)" "y"; then
    if [[ -n "${EDITOR:-}" ]]; then
      "$EDITOR" data/property.json
    elif command -v code >/dev/null 2>&1; then
      code data/property.json
    elif command -v nano >/dev/null 2>&1; then
      nano data/property.json
    else
      info "Open data/property.json in your editor."
      wait_for_enter
    fi
  fi

  # Re-check
  if grep -q '"UPDATE' data/property.json; then
    remaining=$(grep -c '"UPDATE' data/property.json)
    warn "${remaining} UPDATE placeholders remaining. You can finish later."
    info "Run this wizard again after you've filled them in."
  else
    ok "property.json fully populated"
  fi
fi

# ============================================================
step "Google service account"
# ============================================================

ENV_FILE="${REPO_ROOT}/.env"

# Source existing .env if present
if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

if [[ -n "${GOOGLE_SHEETS_KEY_FILE:-}" ]] && [[ -f "${GOOGLE_SHEETS_KEY_FILE}" ]]; then
  ok "Service account key found: ${GOOGLE_SHEETS_KEY_FILE}"
else
  echo "  You need a Google service account to connect to Sheets."
  echo ""
  echo "  Quick version:"
  echo "    1. Go to https://console.cloud.google.com"
  echo "    2. Create a project (or use an existing one)"
  echo "    3. Enable the Google Sheets API"
  echo "    4. IAM & Admin → Service Accounts → Create"
  echo "    5. Download the JSON key file"
  echo ""

  ask "Path to your service account JSON file" sa_path
  sa_path="${sa_path/#\~/$HOME}"

  if [[ -f "$sa_path" ]]; then
    ok "Found: ${sa_path}"
    # Write to .env
    if grep -q "^GOOGLE_SHEETS_KEY_FILE=" "$ENV_FILE" 2>/dev/null; then
      sed -i.bak "s|^GOOGLE_SHEETS_KEY_FILE=.*|GOOGLE_SHEETS_KEY_FILE=${sa_path}|" "$ENV_FILE"
      rm -f "${ENV_FILE}.bak"
    else
      echo "GOOGLE_SHEETS_KEY_FILE=${sa_path}" >> "$ENV_FILE"
    fi
    export GOOGLE_SHEETS_KEY_FILE="$sa_path"
  else
    err "File not found: ${sa_path}"
    info "You can set this later in .env"
  fi
fi

# ============================================================
step "Create or connect the lead sheet"
# ============================================================

if [[ -n "${LEAD_SHEET_ID:-}" ]]; then
  ok "Sheet ID already set: ${LEAD_SHEET_ID}"
  if ask_yn "Keep this sheet? (y = keep, n = create new)" "y"; then
    skip "Keeping existing sheet"
  else
    unset LEAD_SHEET_ID
  fi
fi

if [[ -z "${LEAD_SHEET_ID:-}" ]]; then
  if [[ -n "${GOOGLE_SHEETS_KEY_FILE:-}" ]] && [[ -f "${GOOGLE_SHEETS_KEY_FILE}" ]]; then
    ask "Your email (to share the sheet with you)" user_email

    # Get project name for the sheet title
    sheet_title="RE Lead Gen — Leads"
    if [[ -f data/property.json ]]; then
      pname=$(python3 -c "import json; d=json.load(open('data/property.json')); print(d.get('project_name',''))" 2>/dev/null || echo "")
      if [[ -n "$pname" ]] && [[ "$pname" != *UPDATE* ]]; then
        sheet_title="${pname} — Leads"
      fi
    fi

    info "Creating sheet: ${sheet_title}"
    output=$(python3 scripts/create-sheet.py --email "$user_email" --name "$sheet_title" 2>&1)

    if [[ $? -eq 0 ]]; then
      sheet_id=$(echo "$output" | grep "Sheet ID:" | awk '{print $NF}')
      sheet_url=$(echo "$output" | grep "Sheet created:" | awk '{print $NF}')
      ok "Sheet created: ${sheet_url}"

      # Write to .env
      if grep -q "^LEAD_SHEET_ID=" "$ENV_FILE" 2>/dev/null; then
        sed -i.bak "s|^LEAD_SHEET_ID=.*|LEAD_SHEET_ID=${sheet_id}|" "$ENV_FILE"
        rm -f "${ENV_FILE}.bak"
      else
        echo "LEAD_SHEET_ID=${sheet_id}" >> "$ENV_FILE"
      fi
      export LEAD_SHEET_ID="$sheet_id"
    else
      err "Failed to create sheet"
      echo "$output" | head -5
      info "You can create it manually — see docs/setup.md §3"
    fi
  else
    warn "No service account key — can't create sheet automatically."
    info "Set up the service account first (step 3), then run this again."
  fi
fi

# ============================================================
step "Apps Script (form handler)"
# ============================================================

echo "  This connects your landing page form to the Google Sheet."
echo "  It also fires server-side Meta conversion events."
echo ""
echo "  Steps (manual — Apps Script can't be automated):"
echo ""
echo "    1. Open your Google Sheet"
echo "    2. Extensions → Apps Script"
echo "    3. Delete any existing code"
echo "    4. Paste the contents of: site/form-handler.gs"
echo "    5. File → Project settings → Script properties. Add:"
echo ""
echo -e "       ${BOLD}META_PIXEL_ID${RESET}       — your Pixel ID (from Events Manager)"
echo -e "       ${BOLD}META_CAPI_TOKEN${RESET}     — Conversions API token"
echo -e "       ${BOLD}META_TEST_EVENT_CODE${RESET} — optional, for testing"
echo ""
echo "    6. Deploy → New deployment → Web app"
echo "       Execute as: Me | Access: Anyone"
echo "    7. Copy the /exec URL"

wait_for_enter

ask "Apps Script deployment URL (paste the /exec URL, or press Enter to skip)" apps_url

if [[ -n "$apps_url" ]]; then
  # Update site files
  if grep -q "REPLACE_WITH_DEPLOYED_APPS_SCRIPT_URL" site/index.html 2>/dev/null; then
    sed -i.bak "s|REPLACE_WITH_DEPLOYED_APPS_SCRIPT_URL|${apps_url}|g" site/index.html
    rm -f site/index.html.bak
    ok "Updated site/index.html with Apps Script URL"
  fi
  if grep -q "REPLACE_WITH_DEPLOYED_APPS_SCRIPT_URL" site/thank-you.html 2>/dev/null; then
    sed -i.bak "s|REPLACE_WITH_DEPLOYED_APPS_SCRIPT_URL|${apps_url}|g" site/thank-you.html
    rm -f site/thank-you.html.bak
    ok "Updated site/thank-you.html with Apps Script URL"
  fi
else
  skip "Skipped — you can set this later in the site/ HTML files"
fi

# ============================================================
step "Meta Pixel"
# ============================================================

echo "  Your Meta Pixel tracks visitors and conversion events."
echo ""
echo "  Get your Pixel ID from:"
echo "  Meta Events Manager → Data Sources → your Pixel → Settings"

ask "Meta Pixel ID (numeric, or press Enter to skip)" pixel_id

if [[ -n "$pixel_id" ]]; then
  if grep -q "PIXEL_ID" site/index.html 2>/dev/null; then
    sed -i.bak "s|PIXEL_ID|${pixel_id}|g" site/index.html
    rm -f site/index.html.bak
    ok "Updated site/index.html with Pixel ID"
  fi
  if grep -q "PIXEL_ID" site/thank-you.html 2>/dev/null; then
    sed -i.bak "s|PIXEL_ID|${pixel_id}|g" site/thank-you.html
    rm -f site/thank-you.html.bak
    ok "Updated site/thank-you.html with Pixel ID"
  fi
else
  skip "Skipped — replace PIXEL_ID in site/*.html before launching"
fi

# ============================================================
step "Pipeboard (Meta Ads MCP)"
# ============================================================

echo "  Pipeboard connects Claude to your Meta ad account."
echo ""
echo "    1. Sign up at https://pipeboard.co (free)"
echo "    2. Link your Meta ad account"
echo "    3. Generate an API token"
echo ""
echo "  The .mcp.json config in this repo is already set up."
echo "  Just make sure your Pipeboard token is active."

wait_for_enter
ok "Pipeboard noted — verify with 'claude > /mcp' after setup"

# ============================================================
step "Anthropic API key"
# ============================================================

if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
  ok "ANTHROPIC_API_KEY already set"
else
  echo "  Needed for the daily automated loop (scripts/loop-runner.sh)."
  echo "  Get yours from: https://console.anthropic.com/settings/keys"
  echo ""

  ask "Anthropic API key (sk-ant-..., or press Enter to skip)" api_key

  if [[ -n "$api_key" ]]; then
    if grep -q "^ANTHROPIC_API_KEY=" "$ENV_FILE" 2>/dev/null; then
      sed -i.bak "s|^ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=${api_key}|" "$ENV_FILE"
      rm -f "${ENV_FILE}.bak"
    else
      echo "ANTHROPIC_API_KEY=${api_key}" >> "$ENV_FILE"
    fi
    export ANTHROPIC_API_KEY="$api_key"
    ok "Saved to .env"
  else
    skip "Set ANTHROPIC_API_KEY in .env before running the daily loop"
  fi
fi

# ============================================================
step "Preflight check"
# ============================================================

echo "  Running the full preflight validation..."
echo ""

# Source .env again in case we wrote new values
if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

./scripts/preflight.sh
preflight_exit=$?

# ============================================================
# Summary
# ============================================================

echo ""
echo -e "${BOLD}======================================${RESET}"
echo -e "${BOLD}  SETUP SUMMARY${RESET}"
echo -e "${BOLD}======================================${RESET}"
echo ""

if [[ $preflight_exit -eq 0 ]]; then
  echo -e "  ${GREEN}${BOLD}All checks passed.${RESET}"
  echo ""
  echo "  Next steps:"
  echo "    1. Deploy your landing page:  cp data/property.json site/ && cd site && npx vercel --prod"
  echo "    2. Test the form:             submit a test lead on your site"
  echo "    3. Dry run:                   ./scripts/loop-runner.sh dry_run"
  echo ""
  echo -e "  ${BOLD}Ready to launch ads?${RESET}"
  echo "    Open Claude Code in this project and say:"
  echo ""
  echo -e "    ${CYAN}\"Launch my campaigns\"${RESET}"
  echo ""
  echo "    The campaign launcher will research your best audiences,"
  echo "    generate ads, build your campaign structure, and walk you"
  echo "    through going live — step by step, with your approval at"
  echo "    every stage. No ads experience needed."
  echo ""
else
  echo -e "  ${YELLOW}Some checks still failing — see above.${RESET}"
  echo ""
  echo "  That's fine. Fix what you can and run this again:"
  echo "    ./scripts/onboard.sh"
  echo ""
  echo "  Or run just the check:"
  echo "    ./scripts/preflight.sh"
  echo ""
fi

echo "  Your .env file: ${ENV_FILE}"
echo "  Your property data: data/property.json"
echo ""
echo "  Full docs:"
echo "    docs/HANDOFF.md    — getting started guide"
echo "    docs/setup.md      — detailed reference"
echo "    docs/runbook.md    — operational guide"
echo ""
