#!/usr/bin/env bash
# Pre-launch validation. Run this before driving any traffic.
# Checks every prerequisite and tells you exactly what's missing.
#
# Usage: ./scripts/preflight.sh

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

PASS=0
FAIL=0
WARN=0

pass() { PASS=$((PASS + 1)); echo "  ✓ $1"; }
fail() { FAIL=$((FAIL + 1)); echo "  ✗ $1"; }
warn() { WARN=$((WARN + 1)); echo "  ~ $1"; }

echo ""
echo "RE LEAD GEN — PREFLIGHT CHECK"
echo "=============================="
echo ""

# --- 1. Property data ---
echo "[1/7] Property data"

if [[ ! -f data/property.json ]]; then
  fail "data/property.json missing"
  echo "       → Copy data/property.example.json and fill in your details"
elif grep -q '"UPDATE' data/property.json; then
  count=$(grep -c '"UPDATE' data/property.json)
  fail "data/property.json has ${count} placeholder(s) still set to UPDATE"
  echo "       → Open data/property.json and replace every UPDATE with real content"
  echo "       → See data/property.example.json for a filled-in example"
else
  pass "data/property.json populated (no UPDATE placeholders)"
fi

if python3 -c "
import json, sys
d = json.load(open('data/property.json'))
missing = []
for f in ['project_name']:
  if not d.get(f): missing.append(f)
for f in ['country','region','city','description']:
  if not d.get('location',{}).get(f): missing.append(f'location.{f}')
for f in ['sales_name','sales_phone','sales_whatsapp']:
  if not d.get('contact',{}).get(f): missing.append(f'contact.{f}')
if not d.get('key_selling_points'): missing.append('key_selling_points')
if not d.get('media',{}).get('photos'): missing.append('media.photos')
if missing:
  print('MISSING:' + ','.join(missing))
  sys.exit(1)
" 2>/dev/null; then
  pass "Required fields present"
else
  result=$(python3 -c "
import json, sys
d = json.load(open('data/property.json'))
missing = []
for f in ['project_name']:
  if not d.get(f): missing.append(f)
for f in ['country','region','city','description']:
  if not d.get('location',{}).get(f): missing.append(f'location.{f}')
for f in ['sales_name','sales_phone','sales_whatsapp']:
  if not d.get('contact',{}).get(f): missing.append(f'contact.{f}')
if not d.get('key_selling_points'): missing.append('key_selling_points')
if not d.get('media',{}).get('photos'): missing.append('media.photos')
print(','.join(missing))
" 2>/dev/null)
  fail "Missing fields: ${result}"
fi

echo ""

# --- 2. Python + dependencies ---
echo "[2/7] Python environment"

if command -v python3 >/dev/null 2>&1; then
  pyver=$(python3 --version 2>&1)
  pass "Python installed (${pyver})"
else
  fail "Python 3 not found"
  echo "       → Install Python 3.10+ from https://python.org"
fi

if python3 -c "import gspread" 2>/dev/null; then
  pass "gspread installed"
else
  fail "gspread not installed"
  echo "       → Run: pip install gspread"
fi

if python3 -c "import requests" 2>/dev/null; then
  pass "requests installed"
else
  warn "requests not installed (needed for meta-insights.py fallback)"
  echo "       → Run: pip install requests"
fi

echo ""

# --- 3. Environment variables ---
echo "[3/7] Environment variables"

check_env() {
  local var=$1
  local desc=$2
  local required=$3
  if [[ -n "${!var:-}" ]]; then
    pass "${var} set"
  elif [[ "$required" == "required" ]]; then
    fail "${var} not set — ${desc}"
  else
    warn "${var} not set — ${desc}"
  fi
}

check_env GOOGLE_SHEETS_KEY_FILE "path to Google service account JSON" required
check_env LEAD_SHEET_ID "Google Sheet ID from the URL" required
check_env ANTHROPIC_API_KEY "needed for headless loop-runner.sh" required
check_env META_ACCESS_TOKEN "Meta Graph API token (fallback for cron)" optional
check_env META_AD_ACCOUNT_ID "Meta ad account ID (act_...)" optional

echo ""

# --- 4. Google Sheets connectivity ---
echo "[4/7] Google Sheets"

if [[ -n "${GOOGLE_SHEETS_KEY_FILE:-}" ]] && [[ -n "${LEAD_SHEET_ID:-}" ]]; then
  if python3 scripts/sheet-ops.py new >/dev/null 2>&1; then
    pass "Sheet connection works"
  else
    fail "Cannot connect to Google Sheet"
    echo "       → Check that the service account email has Editor access to the sheet"
    echo "       → Verify GOOGLE_SHEETS_KEY_FILE points to a valid JSON key"
  fi
else
  fail "Skipped — env vars not set (see step 3)"
fi

echo ""

# --- 5. Claude CLI ---
echo "[5/7] Claude Code"

if command -v claude >/dev/null 2>&1; then
  pass "claude CLI found"
else
  fail "claude CLI not found"
  echo "       → Install: npm install -g @anthropic-ai/claude-code"
  echo "       → Then run: claude login"
fi

echo ""

# --- 6. Git submodules ---
echo "[6/7] Git submodules"

if [[ -d vendor/claude-ads/.git ]] || [[ -f vendor/claude-ads/.git ]]; then
  pass "vendor/claude-ads present"
else
  fail "vendor/claude-ads missing"
  echo "       → Run: git submodule update --init --recursive"
fi

if [[ -d vendor/marketingskills/.git ]] || [[ -f vendor/marketingskills/.git ]]; then
  pass "vendor/marketingskills present"
else
  fail "vendor/marketingskills missing"
  echo "       → Run: git submodule update --init --recursive"
fi

echo ""

# --- 7. Landing page ---
echo "[7/7] Landing page"

if [[ -f site/index.html ]]; then
  if grep -q "REPLACE_WITH_DEPLOYED_APPS_SCRIPT_URL" site/index.html; then
    fail "site/index.html still has placeholder Apps Script URL"
    echo "       → Deploy the Apps Script (see docs/setup.md §4) and paste the /exec URL"
  else
    pass "site/index.html has Apps Script URL configured"
  fi
  if grep -q "PIXEL_ID" site/index.html; then
    fail "site/index.html still has placeholder Pixel ID"
    echo "       → Get your Pixel ID from Meta Events Manager and replace PIXEL_ID"
  else
    pass "site/index.html has Pixel ID configured"
  fi
else
  fail "site/index.html missing"
fi

echo ""

# --- Summary ---
echo "=============================="
TOTAL=$((PASS + FAIL + WARN))
echo "  ${PASS} passed, ${FAIL} failed, ${WARN} warnings (${TOTAL} checks)"
echo ""

if [[ $FAIL -eq 0 ]]; then
  echo "  Ready to go. Next step:"
  echo "  → ./scripts/loop-runner.sh dry_run"
  echo ""
  exit 0
else
  echo "  Fix the failures above, then run this again."
  echo ""
  exit 1
fi
