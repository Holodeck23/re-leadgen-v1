#!/usr/bin/env bash
# Entrypoint for the reflective-ops daily loop and hot-lead sweeps.
#
# Usage:
#   scripts/loop-runner.sh                 # full daily run
#   scripts/loop-runner.sh hot_sweep       # 2-hour hot-lead sweep (lighter)
#   scripts/loop-runner.sh dry_run         # analyze + decide, no execution
#   scripts/loop-runner.sh emergency_brake # pause-only mode
#
# Install as cron (example, local time):
#   0 8 * * *  cd /path/to/re-leadgen-v1 && ./scripts/loop-runner.sh >> ops.log 2>&1
#   0 */2 8-20 * * *  cd /path/to/re-leadgen-v1 && ./scripts/loop-runner.sh hot_sweep >> ops.log 2>&1
#
# Required env vars (check .env or shell):
#   GOOGLE_SHEETS_KEY_FILE, LEAD_SHEET_ID          (for scripts/sheet-ops.py)
#   META_ACCESS_TOKEN, META_AD_ACCOUNT_ID          (for scripts/meta-insights.py fallback)
#   ANTHROPIC_API_KEY                              (for claude CLI)
#
# The script uses the Claude CLI to invoke the reflective-operator agent in
# headless mode. The agent reads all required context from the repo.

set -euo pipefail

MODE="${1:-full}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# Source .env if it exists
if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }
log() { echo "[$(ts)] $*"; }

# -- preflight --

if [[ ! -f data/property.json ]]; then
  log "ERROR: data/property.json missing. Halting."
  exit 1
fi

if grep -q '"UPDATE' data/property.json; then
  log "ERROR: data/property.json still has placeholder \"UPDATE\" values. Populate before running."
  exit 1
fi

required_vars=(GOOGLE_SHEETS_KEY_FILE LEAD_SHEET_ID)
for v in "${required_vars[@]}"; do
  if [[ -z "${!v:-}" ]]; then
    log "ERROR: env var $v not set. Halting."
    exit 1
  fi
done

# Daily budget preflight: if today's Meta spend is within cap_headroom_pct of cap, downgrade to emergency_brake.
CAP_USD=$(python3 -c "import json; print(json.load(open('data/kill-scale-rules.json'))['targets']['daily_budget_cap_usd'])")
HEADROOM_PCT=$(python3 -c "import json; print(json.load(open('data/kill-scale-rules.json'))['targets']['cap_headroom_pct'])")
log "Daily budget cap: \$${CAP_USD} (headroom: ${HEADROOM_PCT}%)"

if [[ -n "${META_ACCESS_TOKEN:-}" ]] && [[ -n "${META_AD_ACCOUNT_ID:-}" ]]; then
  SPEND_TODAY=$(python3 scripts/meta-insights.py 2>/dev/null \
    | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    total = sum(
        tf.get('spend', 0)
        for a in data.get('adsets', [])
        for tf in [a.get('timeframes', {}).get('today', {})]
        if not tf.get('empty')
    )
    print(f'{total:.2f}')
except Exception:
    print('')
" 2>/dev/null || echo "")

  if [[ -n "$SPEND_TODAY" ]] && [[ "$SPEND_TODAY" != "" ]]; then
    THRESHOLD=$(python3 -c "print(round(${CAP_USD} * (1.0 - ${HEADROOM_PCT} / 100.0), 2))")
    if python3 -c "import sys; sys.exit(0 if float('${SPEND_TODAY}') >= float('${THRESHOLD}') else 1)" 2>/dev/null; then
      log "WARN: Today's spend (\$${SPEND_TODAY}) is at or above \$${THRESHOLD} threshold. Downgrading to emergency_brake."
      MODE="emergency_brake"
    else
      log "Today's spend: \$${SPEND_TODAY} (threshold: \$${THRESHOLD})"
    fi
  else
    log "WARN: Could not fetch today's spend from Meta. Relying on reflective-ops for cap enforcement."
  fi
else
  log "WARN: META_ACCESS_TOKEN or META_AD_ACCOUNT_ID not set — skipping spend check. Relying on reflective-ops for cap enforcement."
fi

# -- invoke the agent --

log "Running mode=${MODE}"

if ! command -v claude >/dev/null 2>&1; then
  log "ERROR: claude CLI not found. Install Claude Code and run: claude login"
  exit 1
fi

# Use a lock file to prevent "split brain" (multiple concurrent loops).
LOCK_FILE="/tmp/re-leadgen-loop.lock"

# Invoke reflective-operator agent non-interactively within a lock.
(
  flock -n 9 || { log "ERROR: Another loop is already running (lock held). Halting."; exit 1; }
  
  PROMPT="Run the reflective-operator agent in mode=${MODE}. Produce the briefing to stdout. Follow the reflective-ops skill exactly."

  claude \
    --print \
    --agent reflective-operator \
    --allowedTools "Read Bash Grep Glob Skill mcp__meta-ads" \
    <<<"$PROMPT"

) 9>"$LOCK_FILE"

log "Run complete."
