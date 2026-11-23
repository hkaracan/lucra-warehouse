"""Refresh the local warehouse data from a private Google Sheet."""

import argparse
import csv
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import re
import sys
from tempfile import NamedTemporaryFile
from urllib.parse import quote
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from zipfile import BadZipFile


POSITIONS = {f"{line}{number}" for line, end in (("A", 12), ("B", 13), ("C", 13))
             for number in range(1, end + 1)}
ENTRY = re.compile(r"([KLA]?[0-9]+)-([1-6])")
CATALOGUE_URL = "https://inventory.lucramarble.com/data/inventory.json"
OUTPUT = Path(__file__).with_name("bundle-data.js")
MAP_RANGE = "A5:D46"
MAP_TAB_ID = "2131184337"
MAP_TAB_NAME = "Depo Krokisi"


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

    area = quote(f"'{MAP_TAB_NAME}'!{MAP_RANGE}", safe="")
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{quote(sheet_id, safe='')}/values/{area}"
    with urlopen(Request(url, headers={"Authorization": f"Bearer {token}"}), timeout=30) as response:
        return json.load(response)["values"]


def read_link_shared_sheet():
    sheet_id = quote(os.environ["LUCRA_WAREHOUSE_SHEET_ID"], safe="")
    url = (f"https://docs.google.com/spreadsheets/d/{sheet_id}/export"
           f"?format=csv&gid={MAP_TAB_ID}&range={quote(MAP_RANGE, safe='')}")
    try:
        with urlopen(url, timeout=30) as response:
            if response.headers.get_content_type() != "text/csv":
                raise ValueError("The Sheet did not return CSV. Check its link sharing settings.")
            return list(csv.reader(io.StringIO(response.read().decode("utf-8-sig"))))
    except HTTPError as error:
        # Google returns 400 for an Office workbook at the native CSV endpoint.
        if error.code != 400:
            raise
        return read_link_shared_workbook(sheet_id)


def workbook_cell_value(cell):
    value = cell.value
    # Excel can store a numeric code-count entry as a date while displaying
    # the intended entry with its yyyy-m format (for example, 6140-1).
    if (isinstance(value, datetime) and cell.number_format.lower() == "yyyy-m"
            and value.day == 1 and value.time() == datetime.min.time()):
        return f"{value.year}-{value.month}"
    return "" if value is None else value


def read_link_shared_workbook(file_id):
    from openpyxl import load_workbook
    from openpyxl.utils.cell import range_boundaries

    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    with urlopen(url, timeout=30) as response:
        data = response.read()
    try:
        workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except BadZipFile as error:
        raise ValueError("Drive did not return an Excel workbook. Check its link sharing settings.") from error

    try:
        if MAP_TAB_NAME not in workbook.sheetnames:
            raise ValueError(f"The Excel workbook is missing the {MAP_TAB_NAME} tab.")
        min_col, min_row, max_col, max_row = range_boundaries(MAP_RANGE)
        rows = workbook[MAP_TAB_NAME].iter_rows(
            min_col=min_col, min_row=min_row, max_col=max_col, max_row=max_row
        )
        return [[workbook_cell_value(cell) for cell in row] for row in rows]
    finally:
        workbook.close()


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


def add_product_names(records, products):
    names_by_code = {}
    codes_by_number = {}
    for product in products:
        code = (product.get("code") or "").strip().upper()
        name = (product.get("name") or "").strip()
        if not name or not re.fullmatch(r"[A-Z][0-9]+", code):
            continue
        names_by_code.setdefault(code, set()).add(name)
        codes_by_number.setdefault(code[1:], set()).add(code)

    for record in records:
        code = record["code"]
        if code.isdigit():
            candidates = codes_by_number.get(code, set())
            if len(candidates) != 1:
                continue
            code = next(iter(candidates))
        names = names_by_code.get(code, set())
        if len(names) == 1:
            record["name"] = next(iter(names))


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
    sources = parser.add_mutually_exclusive_group()
    sources.add_argument("--from-json", action="store_true", help="Read Google Sheets values JSON from stdin")
    sources.add_argument("--link-shared", action="store_true", help="Read a Sheet shared with anyone who has its link")
    parser.add_argument("--with-product-names", action="store_true", help="Match block codes to the Drive-backed inventory catalogue")
    args = parser.parse_args()
    try:
        if args.from_json:
            rows = json.load(sys.stdin)
        elif args.link_shared:
            rows = read_link_shared_sheet()
        else:
            rows = read_sheet()
        records = collect_bundles(rows)
        if args.with_product_names:
            with urlopen(CATALOGUE_URL, timeout=30) as response:
                products = json.load(response)["products"]
            add_product_names(records, products)
        save_snapshot(records)
    except (ImportError, KeyError, OSError, ValueError) as error:
        parser.exit(1, f"Warehouse refresh failed: {error}\n")
    print(f"Refreshed {len(records)} block locations and {sum(r['count'] for r in records)} bundles.")


if __name__ == "__main__":
    main()
