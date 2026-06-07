"""Create and configure the Google Sheet CRM for re-leadgen-v1.

Creates a new spreadsheet with the correct headers, formatting, and
data validation. Shares it with the user's email so they can see it
in Google Drive.

SETUP:
  pip install gspread
  Set GOOGLE_SHEETS_KEY_FILE to your service account JSON path.

USAGE:
  python scripts/create-sheet.py --email you@example.com
  python scripts/create-sheet.py --email you@example.com --name "My Project Leads"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

try:
    import gspread
except ImportError:
    print("Run: pip install gspread", file=sys.stderr)
    sys.exit(1)


SHEET_COLUMNS: tuple[str, ...] = (
    "timestamp", "name", "email", "phone", "interest",
    "budget", "timeline", "message", "source",
    "score", "status", "notes", "follow_up_date",
)

STATUS_VALUES: tuple[str, ...] = (
    "new", "contacted", "nurture", "qualified",
    "handoff", "closed", "lost", "duplicate",
)

INTEREST_VALUES: tuple[str, ...] = (
    "lot", "unit", "investment", "visit", "exploring", "info",
)

HEADER_COLOR = {"red": 0.14, "green": 0.14, "blue": 0.14}
HEADER_TEXT_COLOR = {"red": 1.0, "green": 1.0, "blue": 1.0}


def create_sheet(
    key_file: str,
    user_email: str,
    sheet_name: str = "RE Lead Gen — Leads",
) -> dict[str, str]:
    """Create a new spreadsheet and return its ID and URL."""
    gc = gspread.service_account(filename=key_file)

    spreadsheet = gc.create(sheet_name)
    ws = spreadsheet.sheet1
    ws.update_title("Leads")

    # Write headers
    ws.update("A1:M1", [list(SHEET_COLUMNS)])

    # Format header row
    ws.format("A1:M1", {
        "backgroundColor": HEADER_COLOR,
        "textFormat": {
            "foregroundColorStyle": {"rgbColor": HEADER_TEXT_COLOR},
            "bold": True,
            "fontSize": 10,
        },
        "horizontalAlignment": "CENTER",
    })

    # Freeze header row
    ws.freeze(rows=1)

    # Set column widths for readability
    col_widths: dict[str, int] = {
        "A": 160,  # timestamp
        "B": 140,  # name
        "C": 200,  # email
        "D": 130,  # phone
        "E": 100,  # interest
        "F": 100,  # budget
        "G": 100,  # timeline
        "H": 300,  # message
        "I": 200,  # source
        "J": 60,   # score
        "K": 90,   # status
        "L": 300,  # notes
        "M": 110,  # follow_up_date
    }

    requests_batch: list[dict[str, Any]] = []
    for col_letter, width in col_widths.items():
        col_index = ord(col_letter) - ord("A")
        requests_batch.append({
            "updateDimensionProperties": {
                "range": {
                    "sheetId": ws.id,
                    "dimension": "COLUMNS",
                    "startIndex": col_index,
                    "endIndex": col_index + 1,
                },
                "properties": {"pixelSize": width},
                "fields": "pixelSize",
            }
        })

    # Data validation: status column
    status_rule = {
        "setDataValidation": {
            "range": {
                "sheetId": ws.id,
                "startRowIndex": 1,
                "endRowIndex": 1000,
                "startColumnIndex": 10,  # K = status
                "endColumnIndex": 11,
            },
            "rule": {
                "condition": {
                    "type": "ONE_OF_LIST",
                    "values": [{"userEnteredValue": v} for v in STATUS_VALUES],
                },
                "showCustomUi": True,
                "strict": False,
            },
        }
    }
    requests_batch.append(status_rule)

    # Data validation: interest column
    interest_rule = {
        "setDataValidation": {
            "range": {
                "sheetId": ws.id,
                "startRowIndex": 1,
                "endRowIndex": 1000,
                "startColumnIndex": 4,  # E = interest
                "endColumnIndex": 5,
            },
            "rule": {
                "condition": {
                    "type": "ONE_OF_LIST",
                    "values": [{"userEnteredValue": v} for v in INTEREST_VALUES],
                },
                "showCustomUi": True,
                "strict": False,
            },
        }
    }
    requests_batch.append(interest_rule)

    # Conditional formatting: hot leads (score >= 70) highlighted
    hot_lead_rule = {
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [{
                    "sheetId": ws.id,
                    "startRowIndex": 1,
                    "endRowIndex": 1000,
                    "startColumnIndex": 0,
                    "endColumnIndex": 13,
                }],
                "booleanRule": {
                    "condition": {
                        "type": "CUSTOM_FORMULA",
                        "values": [{"userEnteredValue": "=$J2>=70"}],
                    },
                    "format": {
                        "backgroundColor": {"red": 0.85, "green": 0.95, "blue": 0.85},
                    },
                },
            },
            "index": 0,
        }
    }
    requests_batch.append(hot_lead_rule)

    # Conditional formatting: duplicate/lost leads greyed out
    grey_rule = {
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [{
                    "sheetId": ws.id,
                    "startRowIndex": 1,
                    "endRowIndex": 1000,
                    "startColumnIndex": 0,
                    "endColumnIndex": 13,
                }],
                "booleanRule": {
                    "condition": {
                        "type": "CUSTOM_FORMULA",
                        "values": [{"userEnteredValue": '=OR($K2="duplicate",$K2="lost")'}],
                    },
                    "format": {
                        "textFormat": {
                            "foregroundColorStyle": {
                                "rgbColor": {"red": 0.6, "green": 0.6, "blue": 0.6},
                            },
                        },
                    },
                },
            },
            "index": 1,
        }
    }
    requests_batch.append(grey_rule)

    if requests_batch:
        spreadsheet.batch_update({"requests": requests_batch})

    # Share with the user
    spreadsheet.share(user_email, perm_type="user", role="writer")

    return {
        "id": spreadsheet.id,
        "url": spreadsheet.url,
        "title": sheet_name,
    }


def _main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Create the RE Lead Gen CRM sheet")
    parser.add_argument("--email", required=True, help="Your email (to share the sheet with you)")
    parser.add_argument("--name", default="RE Lead Gen — Leads", help="Sheet name")
    parser.add_argument("--key-file", default=None, help="Service account JSON (or set GOOGLE_SHEETS_KEY_FILE)")
    args = parser.parse_args(argv[1:])

    key_file = args.key_file or os.environ.get("GOOGLE_SHEETS_KEY_FILE")
    if not key_file:
        print("Set GOOGLE_SHEETS_KEY_FILE or pass --key-file", file=sys.stderr)
        return 1

    if not os.path.isfile(key_file):
        print(f"Key file not found: {key_file}", file=sys.stderr)
        return 1

    print(f"Creating sheet '{args.name}'...")
    result = create_sheet(key_file, args.email, args.name)

    print()
    print(f"  Sheet created: {result['url']}")
    print(f"  Sheet ID:      {result['id']}")
    print(f"  Shared with:   {args.email}")
    print()
    print(f"  Add this to your .env:")
    print(f"  LEAD_SHEET_ID={result['id']}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
