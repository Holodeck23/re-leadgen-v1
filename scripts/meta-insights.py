"""Pull multi-timeframe Meta Ads insights for the reflective-ops loop.

Returns, for every active ad set under the configured ad account, metrics across
four timeframes: today / yesterday / last_7_days / lifetime.

The reflective-ops skill is supposed to call the Meta Ads MCP directly from within
a Claude session. This script exists as a standalone fallback when the loop is run
from cron (no MCP available) or for debugging.

SETUP:
  pip install requests
  Env vars: META_ACCESS_TOKEN, META_AD_ACCOUNT_ID (format act_1234567890)

USAGE:
  python scripts/meta-insights.py                 # JSON blob to stdout
  python scripts/meta-insights.py --adset ID      # single ad set only
  python scripts/meta-insights.py --since 2026-04-01
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

try:
    import requests
except ImportError:
    print("Run: pip install requests", file=sys.stderr)
    sys.exit(1)


META_GRAPH = "https://graph.facebook.com/v20.0"

INSIGHT_FIELDS = (
    "spend,impressions,reach,frequency,clicks,ctr,cpm,cpc,"
    "actions,action_values,video_p25_watched_actions,"
    "video_p75_watched_actions,video_3_sec_watched_actions"
)

TIMEFRAMES: tuple[tuple[str, dict[str, str]], ...] = (
    ("today", {"date_preset": "today"}),
    ("yesterday", {"date_preset": "yesterday"}),
    ("last_7_days", {"date_preset": "last_7d"}),
    ("lifetime", {"date_preset": "maximum"}),
)


@dataclass(frozen=True)
class Config:
    access_token: str
    account_id: str


def _cfg() -> Config:
    token = os.environ.get("META_ACCESS_TOKEN")
    account = os.environ.get("META_AD_ACCOUNT_ID")
    if not token or not account:
        print("Set META_ACCESS_TOKEN and META_AD_ACCOUNT_ID env vars", file=sys.stderr)
        sys.exit(1)
    if not account.startswith("act_"):
        account = f"act_{account}"
    return Config(access_token=token, account_id=account)


def _get(path: str, params: dict[str, Any]) -> dict[str, Any]:
    params = {**params, "access_token": _cfg().access_token}
    r = requests.get(f"{META_GRAPH}{path}", params=params, timeout=30)
    if not r.ok:
        raise RuntimeError(f"Meta API {r.status_code}: {r.text[:300]}")
    return r.json()


def list_active_adsets() -> list[dict[str, Any]]:
    cfg = _cfg()
    data = _get(f"/{cfg.account_id}/adsets", {
        "fields": "id,name,status,effective_status,campaign_id,daily_budget,bid_strategy,targeting",
        "limit": 200,
    })
    rows = data.get("data", [])
    return [a for a in rows if a.get("effective_status") in {"ACTIVE", "LEARNING"}]


def _extract_leads_from_actions(actions: list[dict[str, Any]] | None) -> int:
    if not actions:
        return 0
    for a in actions:
        if a.get("action_type") in {"lead", "onsite_conversion.lead_grouped",
                                     "offsite_conversion.fb_pixel_lead"}:
            try:
                return int(float(a.get("value", 0)))
            except (TypeError, ValueError):
                return 0
    return 0


def _extract_video_3s(actions: list[dict[str, Any]] | None) -> int:
    if not actions:
        return 0
    for a in actions:
        if a.get("action_type") == "video_view":
            try:
                return int(float(a.get("value", 0)))
            except (TypeError, ValueError):
                return 0
    return 0


def _derive_kpis(row: dict[str, Any]) -> dict[str, Any]:
    spend = float(row.get("spend", 0) or 0)
    impressions = int(row.get("impressions", 0) or 0)
    reach = int(row.get("reach", 0) or 0)
    frequency = float(row.get("frequency", 0) or 0)
    clicks = int(row.get("clicks", 0) or 0)
    ctr = float(row.get("ctr", 0) or 0) / 100.0
    cpm = float(row.get("cpm", 0) or 0)
    cpc = float(row.get("cpc", 0) or 0)

    actions = row.get("actions", [])
    leads = _extract_leads_from_actions(actions)
    video_3s = _extract_video_3s(row.get("video_3_sec_watched_actions", []))

    cpl = spend / leads if leads > 0 else None
    hook_rate_3s = video_3s / impressions if impressions > 0 else None

    return {
        "spend": spend,
        "impressions": impressions,
        "reach": reach,
        "frequency": round(frequency, 3),
        "clicks": clicks,
        "ctr": round(ctr, 4),
        "cpm": round(cpm, 2),
        "cpc": round(cpc, 2),
        "leads": leads,
        "cpl": round(cpl, 2) if cpl is not None else None,
        "hook_rate_3s": round(hook_rate_3s, 4) if hook_rate_3s is not None else None,
    }


def insights_for_adset(adset_id: str, timeframe: str, params: dict[str, str]) -> dict[str, Any]:
    data = _get(f"/{adset_id}/insights", {"fields": INSIGHT_FIELDS, **params})
    rows = data.get("data", [])
    if not rows:
        return {"timeframe": timeframe, "empty": True}
    return {"timeframe": timeframe, **_derive_kpis(rows[0])}


def snapshot(adset_filter: str | None = None) -> dict[str, Any]:
    adsets = list_active_adsets()
    if adset_filter:
        adsets = [a for a in adsets if a.get("id") == adset_filter]

    out: list[dict[str, Any]] = []
    for a in adsets:
        timeframes: dict[str, Any] = {}
        for name, params in TIMEFRAMES:
            try:
                timeframes[name] = insights_for_adset(a["id"], name, params)
            except RuntimeError as e:
                timeframes[name] = {"timeframe": name, "error": str(e)}
        daily_budget_cents = int(a.get("daily_budget") or 0)
        out.append({
            "adset_id": a["id"],
            "adset_name": a.get("name", ""),
            "campaign_id": a.get("campaign_id", ""),
            "effective_status": a.get("effective_status", ""),
            "daily_budget_usd": round(daily_budget_cents / 100.0, 2),
            "timeframes": timeframes,
        })

    return {
        "as_of": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ad_account_id": _cfg().account_id,
        "adsets": out,
    }


def _main(argv: list[str]) -> int:
    adset_filter: str | None = None
    if "--adset" in argv:
        i = argv.index("--adset")
        if i + 1 < len(argv):
            adset_filter = argv[i + 1]
    print(json.dumps(snapshot(adset_filter=adset_filter), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
