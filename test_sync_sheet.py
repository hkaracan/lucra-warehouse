import io
import unittest
from datetime import datetime
from unittest.mock import patch

from openpyxl import Workbook

import sync_sheet


class WorkbookImportTests(unittest.TestCase):
    def workbook_bytes(self, *, count=1, number_format="yyyy-m"):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = sync_sheet.MAP_TAB_NAME
        for row, position in enumerate(sorted(sync_sheet.POSITIONS), start=6):
            sheet.cell(row, 1, position)
        row = next(row for row in range(6, 44) if sheet.cell(row, 1).value == "C8")
        sheet.cell(row, 2, "K6388-4")
        for column, year in ((3, 6140), (4, 4768)):
            cell = sheet.cell(row, column, datetime(year, count, 1))
            cell.number_format = number_format
        data = io.BytesIO()
        workbook.save(data)
        workbook.close()
        return data.getvalue()

    def import_records(self, **kwargs):
        with patch.object(sync_sheet, "urlopen", return_value=io.BytesIO(self.workbook_bytes(**kwargs))):
            rows = sync_sheet.read_link_shared_workbook("test-file")
        return sync_sheet.collect_bundles(rows)

    def test_recovers_displayed_numeric_codes_from_excel_dates(self):
        self.assertEqual(self.import_records(), [
            {"code": "K6388", "position": "C8", "count": 4},
            {"code": "6140", "position": "C8", "count": 1},
            {"code": "4768", "position": "C8", "count": 1},
        ])

    def test_other_date_formats_still_fail_validation(self):
        with self.assertRaisesRegex(ValueError, "C8: invalid entry"):
            self.import_records(number_format="yyyy-mm-dd")

    def test_recovered_count_must_be_between_one_and_six(self):
        with self.assertRaisesRegex(ValueError, "C8: invalid entry"):
            self.import_records(count=7)

    def test_recovered_counts_cannot_exceed_position_capacity(self):
        with self.assertRaisesRegex(ValueError, "C8: 8 bundles exceeds"):
            self.import_records(count=2)


if __name__ == "__main__":
    unittest.main()
