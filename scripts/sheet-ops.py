"""
Google Sheets operations for the lead gen system.

Uses gspread + service account for programmatic access.
For one-off reads, you can also just export the sheet as CSV.

SETUP:
1. pip install gspread
2. Create a service account in Google Cloud Console
3. Download the JSON key file
4. Share the Google Sheet with the service account email
5. Set GOOGLE_SHEETS_KEY_FILE env var to the path of the JSON key
6. Set LEAD_SHEET_ID env var to the Google Sheet ID
"""

import os
import json
import sys
from datetime import datetime, timedelta

try:
    import gspread
except ImportError:
    print("Run: pip install gspread")
    sys.exit(1)


SHEET_COLUMNS = [
    "timestamp", "name", "email", "phone", "interest",
    "budget", "timeline", "message", "source",
    "score", "status", "notes", "follow_up_date"
]


def get_sheet():
    key_file = os.environ.get("GOOGLE_SHEETS_KEY_FILE")
    sheet_id = os.environ.get("LEAD_SHEET_ID")

    if not key_file or not sheet_id:
        print("Set GOOGLE_SHEETS_KEY_FILE and LEAD_SHEET_ID environment variables")
        sys.exit(1)

    gc = gspread.service_account(filename=key_file)
    spreadsheet = gc.open_by_key(sheet_id)
    return spreadsheet.sheet1


def get_new_leads():
    """Fetch all leads with status 'new'."""
    sheet = get_sheet()
    records = sheet.get_all_records()
    return [r for r in records if r.get("status", "").lower() == "new"]


def get_all_leads():
    """Fetch all leads."""
    sheet = get_sheet()
    return sheet.get_all_records()


def get_leads_due_followup():
    """Fetch leads whose follow_up_date is today or earlier."""
    sheet = get_sheet()
    records = sheet.get_all_records()
    today = datetime.now().strftime("%Y-%m-%d")
    return [
        r for r in records
        if r.get("follow_up_date", "") and r["follow_up_date"] <= today
        and r.get("status", "") not in ("closed", "cold")
    ]


def update_lead(row_number, score, status, notes, follow_up_date):
    """Update scoring fields for a lead. row_number is 1-indexed (header = row 1)."""
    sheet = get_sheet()
    # score is column 10, status 11, notes 12, follow_up_date 13
    sheet.update_cell(row_number, 10, score)
    sheet.update_cell(row_number, 11, status)
    sheet.update_cell(row_number, 12, notes)
    sheet.update_cell(row_number, 13, follow_up_date)


def export_csv(output_path="leads.csv"):
    """Export all leads to CSV for offline processing."""
    import csv
    records = get_all_leads()
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SHEET_COLUMNS)
        writer.writeheader()
        writer.writerows(records)
    print(f"Exported {len(records)} leads to {output_path}")


def import_scores(scores_json):
    """
    Bulk update scores from a JSON array.
    Each item: { "row": N, "score": N, "status": "...", "notes": "...", "follow_up_date": "..." }
    """
    sheet = get_sheet()
    scores = json.loads(scores_json) if isinstance(scores_json, str) else scores_json
    for item in scores:
        row = item["row"]
        sheet.update_cell(row, 10, item.get("score", ""))
        sheet.update_cell(row, 11, item.get("status", ""))
        sheet.update_cell(row, 12, item.get("notes", ""))
        sheet.update_cell(row, 13, item.get("follow_up_date", ""))
    print(f"Updated {len(scores)} leads")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python sheet-ops.py [new|all|due|export]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "new":
        leads = get_new_leads()
        print(json.dumps(leads, indent=2))
    elif command == "all":
        leads = get_all_leads()
        print(json.dumps(leads, indent=2))
    elif command == "due":
        leads = get_leads_due_followup()
        print(json.dumps(leads, indent=2))
    elif command == "export":
        export_csv()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
