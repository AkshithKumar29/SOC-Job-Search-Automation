"""Read/write smoke test for the existing private Google Sheets workbook."""

from datetime import datetime, timezone
import json
import os
import sys
from uuid import uuid4

import gspread
from google.oauth2.service_account import Credentials


WORKSHEETS = ("UK_JOBS", "INDIA_JOBS", "EU_JOBS", "EXECUTION_LOGS")
SCOPES = ("https://www.googleapis.com/auth/spreadsheets",)


def run() -> None:
    raw_credentials = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    sheet_id = os.environ.get("GOOGLE_SHEET_ID", "")
    if not raw_credentials or not sheet_id:
        raise ValueError("Missing required Actions secrets: GOOGLE_SERVICE_ACCOUNT_JSON and/or GOOGLE_SHEET_ID")

    try:
        info = json.loads(raw_credentials)
        if info.get("type") != "service_account":
            raise ValueError("Credential is not a service account key")
        credentials = Credentials.from_service_account_info(info, scopes=SCOPES)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise ValueError("Invalid GOOGLE_SERVICE_ACCOUNT_JSON") from None
    finally:
        # The JSON key never goes to disk or stdout.
        del raw_credentials

    client = gspread.authorize(credentials)
    workbook = client.open_by_key(sheet_id)
    existing = {worksheet.title: worksheet for worksheet in workbook.worksheets()}
    for title in WORKSHEETS:
        if title not in existing:
            existing[title] = workbook.add_worksheet(title=title, rows=1000, cols=26)
            print(f"Created worksheet: {title}")
        else:
            print(f"Verified worksheet: {title}")

    log_sheet = existing["EXECUTION_LOGS"]
    marker = f"SHEETS_TEST_{uuid4().hex}"
    row = [marker, datetime.now(timezone.utc).isoformat(), "GOOGLE_SHEETS_TEST", "SUCCESS"]
    log_sheet.append_row(row, value_input_option="RAW")
    found = log_sheet.find(marker, in_column=1)
    if found is None or log_sheet.row_values(found.row)[: len(row)] != row:
        raise RuntimeError("Appended test entry could not be read back")
    print("SUCCESS: service account read/write access and all four worksheets verified; test entry read back.")


if __name__ == "__main__":
    try:
        run()
    except (gspread.exceptions.APIError, gspread.exceptions.SpreadsheetNotFound):
        print("FAILURE: Google Sheets access failed. Check the spreadsheet ID, API enablement, and editor sharing with the service account.", file=sys.stderr)
        sys.exit(1)
    except (ValueError, RuntimeError) as exc:
        print(f"FAILURE: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception:
        # Do not emit a traceback: Google client exceptions may include private request data.
        print("FAILURE: unexpected Google Sheets integration error; credentials and request details withheld.", file=sys.stderr)
        sys.exit(1)
