"""Refresh the local warehouse data from a private Google Sheet."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
from tempfile import NamedTemporaryFile
from urllib.parse import quote
from urllib.request import Request, urlopen


POSITIONS = {f"{line}{number}" for line, end in (("A", 12), ("B", 13), ("C", 13))
             for number in range(1, end + 1)}
ENTRY = re.compile(r"([KLA]?[0-9]+)-([1-6])")
OUTPUT = Path(__file__).with_name("bundle-data.js")


def read_sheet():
    sheet_id = os.environ["LUCRA_WAREHOUSE_SHEET_ID"]
    token = os.environ.get("LUCRA_SHEETS_ACCESS_TOKEN")
    if not token:
        import google.auth
        from google.auth.transport.requests import Request as GoogleRequest

        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        credentials.refresh(GoogleRequest())
        token = credentials.token

    area = quote("'Depo Krokisi'!A5:D46", safe="")
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{quote(sheet_id, safe='')}/values/{area}"
    with urlopen(Request(url, headers={"Authorization": f"Bearer {token}"}), timeout=30) as response:
        return json.load(response)["values"]


def collect_bundles(rows):
    records = []
    seen = set()
    for sheet_row, row in enumerate(rows, start=5):
        if not row:
            continue
        position = str(row[0]).strip()
        if position in {"", "A", "B", "C", "Seleksiyon Alanı"}:
            continue
        if position not in POSITIONS or position in seen:
            raise ValueError(f"Unexpected or repeated position on Sheet row {sheet_row}.")
        seen.add(position)
        codes = set()
        total = 0
        for raw in row[1:]:
            entry = str(raw).strip().upper()
            if not entry:
                continue
            match = ENTRY.fullmatch(entry)
            if not match:
                raise ValueError(f"{position}: invalid entry. Use a code and count like K6155-5.")
            code, quantity = match.groups()
            if code in codes:
                raise ValueError(f"{position}: repeated block code {code}. Combine its counts.")
            codes.add(code)
            count = int(quantity)
            total += count
            records.append({"code": code, "position": position, "count": count})
        if total > 6:
            raise ValueError(f"{position}: {total} bundles exceeds its six-bundle capacity.")
    if seen != POSITIONS:
        raise ValueError(f"Missing positions: {', '.join(sorted(POSITIONS - seen))}")
    if not records:
        raise ValueError("The Sheet has no bundle entries. The previous website data was kept.")
    return records


def save_snapshot(records):
    refreshed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=OUTPUT.parent, delete=False) as handle:
        temp = Path(handle.name)
        try:
            handle.write("// Generated from Depo Krokisi. Corridor sides are unconfirmed.\n")
            handle.write(f"const bundleDataUpdatedAt = {json.dumps(refreshed_at)};\n")
            handle.write("const bundles = [\n")
            for record in records:
                handle.write(f"  {json.dumps(record, separators=(',', ':'))},\n")
            handle.write("];\n")
            handle.close()
            temp.chmod(0o644)
            temp.replace(OUTPUT)
        finally:
            temp.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-json", action="store_true", help="Read Google Sheets values JSON from stdin")
    args = parser.parse_args()
    try:
        rows = json.load(sys.stdin) if args.from_json else read_sheet()
        records = collect_bundles(rows)
        save_snapshot(records)
    except (ImportError, KeyError, OSError, ValueError) as error:
        parser.exit(1, f"Warehouse refresh failed: {error}\n")
    print(f"Refreshed {len(records)} block locations and {sum(r['count'] for r in records)} bundles.")


if __name__ == "__main__":
    main()
