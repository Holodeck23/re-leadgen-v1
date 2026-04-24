"""Google Sheets operations for the RE lead gen system.

Uses gspread + service account. Canonical CRM backbone.

SETUP:
  1. pip install gspread
  2. Create a service account in Google Cloud Console and download JSON key.
  3. Share the Google Sheet with the service account email.
  4. Set env vars: GOOGLE_SHEETS_KEY_FILE, LEAD_SHEET_ID.

USAGE:
  python scripts/sheet-ops.py new            # JSON array of status=new leads
  python scripts/sheet-ops.py all            # JSON array of all leads
  python scripts/sheet-ops.py due            # JSON array of follow-ups due today
  python scripts/sheet-ops.py export         # Export all to leads.csv
  python scripts/sheet-ops.py quality-by-adset [--window-days 14]
                                             # Avg lead score per utm_campaign (ad set proxy)
  python scripts/sheet-ops.py import-scores scored.json
                                             # Bulk upsert scored leads (batch write)
"""

from __future__ import annotations

import csv
import json
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

try:
    import gspread
    from gspread.utils import rowcol_to_a1
except ImportError:
    print("Run: pip install gspread", file=sys.stderr)
    sys.exit(1)


SHEET_COLUMNS: tuple[str, ...] = (
    "timestamp", "name", "email", "phone", "interest",
    "budget", "timeline", "message", "source",
    "score", "status", "notes", "follow_up_date",
)

SCORE_COL = 10
STATUS_COL = 11
NOTES_COL = 12
FOLLOW_UP_COL = 13


@dataclass(frozen=True)
class AdSetQuality:
    adset_key: str
    leads: int
    avg_score: float
    hot_count: int
    qualified_rate: float


LIMIT_LEADS = 1000


def get_sheet() -> "gspread.Worksheet":
    key_file = os.environ.get("GOOGLE_SHEETS_KEY_FILE")
    sheet_id = os.environ.get("LEAD_SHEET_ID")
    if not key_file or not sheet_id:
        print("Set GOOGLE_SHEETS_KEY_FILE and LEAD_SHEET_ID environment variables", file=sys.stderr)
        sys.exit(1)
    gc = gspread.service_account(filename=key_file)
    return gc.open_by_key(sheet_id).sheet1


def get_new_leads() -> list[dict[str, Any]]:
    sheet = get_sheet()
    # Read the last N rows instead of the entire sheet for performance
    last_row = sheet.row_count
    if last_row > LIMIT_LEADS:
        records = sheet.get_all_records(head=1, offset=last_row - LIMIT_LEADS)
    else:
        records = sheet.get_all_records()
    return [r for r in records if str(r.get("status", "")).lower() == "new"]


def get_all_leads() -> list[dict[str, Any]]:
    sheet = get_sheet()
    last_row = sheet.row_count
    if last_row > LIMIT_LEADS:
        return sheet.get_all_records(head=1, offset=last_row - LIMIT_LEADS)
    return sheet.get_all_records()


def get_leads_due_followup() -> list[dict[str, Any]]:
    records = get_all_leads()
    today = datetime.now().strftime("%Y-%m-%d")
    excluded = {"closed", "cold", "lost", "duplicate"}
    return [
        r for r in records
        if r.get("follow_up_date", "")
        and str(r["follow_up_date"]) <= today
        and str(r.get("status", "")).lower() not in excluded
    ]


def _adset_id_from_notes(notes: str) -> str:
    """Pull Meta's ad-set id out of the notes column if form-handler.gs recorded one.

    form-handler.gs writes notes as '; '-delimited key=value pairs:
      "lead_id=<uuid>; event_id=<uuid>; return_visitor=false; adset_id=120200000000001234"
    The id comes from the {{adset.id}} URL macro on the Meta ad and is the
    only join key that survives campaign/ad renames.
    """
    if not notes:
        return ""
    for token in str(notes).split(";"):
        token = token.strip()
        if token.lower().startswith("adset_id="):
            _, _, val = token.partition("=")
            return val.strip()
    return ""


def _adset_key_from_source(source: str) -> str:
    """Fallback attribution key from the UTM-encoded source column.

    form-handler.gs writes source as a pipe-delimited string:
      "utm_source=ig|utm_medium=cpc|utm_campaign=lots-apr|utm_content=reel-03|..."
    We treat utm_campaign + utm_content as the closest proxy for ad set + ad.
    Only used when no adset_id is present (organic/referral traffic or legacy rows).
    """
    if not source:
        return "direct"
    parts: dict[str, str] = {}
    for token in str(source).split("|"):
        if "=" in token:
            key, _, val = token.partition("=")
            parts[key.strip().lower()] = val.strip()
    campaign = parts.get("utm_campaign", "")
    content = parts.get("utm_content", "")
    if campaign and content:
        return f"{campaign}::{content}"
    if campaign:
        return campaign
    if parts:
        return parts.get("utm_source", "direct")
    return str(source).strip() or "direct"


def _attribution_key(record: dict[str, Any]) -> str:
    """Canonical ad-set key. Prefers Meta adset_id from notes; falls back to UTM."""
    adset_id = _adset_id_from_notes(str(record.get("notes", "")))
    if adset_id:
        return f"adset:{adset_id}"
    return _adset_key_from_source(str(record.get("source", "")))


def _parse_timestamp(ts: str) -> datetime | None:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(ts), fmt)
        except ValueError:
            continue
    return None


def quality_by_adset(window_days: int = 14, hot_threshold: int = 70, qualified_threshold: int = 40) -> dict[str, Any]:
    """Aggregate lead quality per ad-set proxy from the sheet.

    Output feeds the reflective-ops lead-quality gate.
    """
    records = get_all_leads()
    # 1-day attribution buffer: We look back window_days + 1 to account for 
    # leads who clicked an ad yesterday but submitted the form today.
    cutoff = datetime.now() - timedelta(days=window_days + 1)

    buckets: dict[str, list[int]] = defaultdict(list)
    for r in records:
        ts = _parse_timestamp(str(r.get("timestamp", "")))
        if ts is None or ts < cutoff:
            continue
        try:
            score = int(r.get("score") or 0)
        except (TypeError, ValueError):
            score = 0
        if score == 0 and str(r.get("status", "")).lower() == "new":
            continue
        key = _attribution_key(r)
        buckets[key].append(score)

    results: list[AdSetQuality] = []
    for key, scores in buckets.items():
        n = len(scores)
        if n == 0:
            continue
        avg = sum(scores) / n
        hot = sum(1 for s in scores if s >= hot_threshold)
        qualified = sum(1 for s in scores if s >= qualified_threshold)
        results.append(AdSetQuality(
            adset_key=key,
            leads=n,
            avg_score=round(avg, 2),
            hot_count=hot,
            qualified_rate=round(qualified / n, 3),
        ))

    results.sort(key=lambda q: q.avg_score, reverse=True)
    return {
        "as_of": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "window_days": window_days,
        "by_adset": [q.__dict__ for q in results],
    }


def write_lead(row_number: int, *, score: int | str | None = None, status: str | None = None,
               notes: str | None = None, follow_up_date: str | None = None) -> None:
    """Update one lead row using batch_update (one API call for all columns)."""
    sheet = get_sheet()
    updates: list[dict[str, Any]] = []
    if score is not None:
        updates.append({"range": rowcol_to_a1(row_number, SCORE_COL), "values": [[score]]})
    if status is not None:
        updates.append({"range": rowcol_to_a1(row_number, STATUS_COL), "values": [[status]]})
    if notes is not None:
        updates.append({"range": rowcol_to_a1(row_number, NOTES_COL), "values": [[notes]]})
    if follow_up_date is not None:
        updates.append({"range": rowcol_to_a1(row_number, FOLLOW_UP_COL), "values": [[follow_up_date]]})
    if updates:
        sheet.batch_update(updates)


def import_scores(scores: list[dict[str, Any]]) -> int:
    """Bulk update many rows with one batch_update call. Each item: {row, score, status, notes, follow_up_date}."""
    sheet = get_sheet()
    updates: list[dict[str, Any]] = []
    for item in scores:
        row = int(item["row"])
        for col, key in ((SCORE_COL, "score"), (STATUS_COL, "status"),
                        (NOTES_COL, "notes"), (FOLLOW_UP_COL, "follow_up_date")):
            if key in item:
                updates.append({"range": rowcol_to_a1(row, col), "values": [[item[key]]]})
    if updates:
        sheet.batch_update(updates)
    return len(scores)


def export_csv(output_path: str = "leads.csv") -> None:
    records = get_all_leads()
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SHEET_COLUMNS)
        writer.writeheader()
        writer.writerows(records)
    print(f"Exported {len(records)} leads to {output_path}")


def _main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1
    command = argv[1]

    if command == "new":
        print(json.dumps(get_new_leads(), indent=2, default=str))
    elif command == "all":
        print(json.dumps(get_all_leads(), indent=2, default=str))
    elif command == "due":
        print(json.dumps(get_leads_due_followup(), indent=2, default=str))
    elif command == "export":
        output = argv[2] if len(argv) > 2 else "leads.csv"
        export_csv(output)
    elif command == "quality-by-adset":
        window = 14
        if "--window-days" in argv:
            i = argv.index("--window-days")
            if i + 1 < len(argv):
                window = int(argv[i + 1])
        print(json.dumps(quality_by_adset(window_days=window), indent=2, default=str))
    elif command == "import-scores":
        if len(argv) < 3:
            print("Usage: sheet-ops.py import-scores <path-to-json>", file=sys.stderr)
            return 1
        with open(argv[2], encoding="utf-8") as f:
            scores = json.load(f)
        n = import_scores(scores)
        print(f"Updated {n} leads")
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
