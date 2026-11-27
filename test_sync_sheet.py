import io
import socket
import unittest
from datetime import datetime
from http.client import IncompleteRead
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from openpyxl import Workbook

import sync_sheet


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.log = io.StringIO()
        self.stderr = patch.object(sync_sheet.sys, "stderr", self.log)
        self.stderr.start()
        self.addCleanup(self.stderr.stop)

    def test_temporary_dns_failure_recovers_with_backoff(self):
        error = URLError(socket.gaierror(socket.EAI_AGAIN, "Temporary failure in name resolution"))
        with patch.object(sync_sheet, "urlopen", side_effect=[error, error, io.BytesIO(b"ok")]) as fetch:
            with patch.object(sync_sheet, "sleep") as sleep:
                self.assertEqual(sync_sheet.download("https://example.test", "Test source"), b"ok")
        self.assertEqual(fetch.call_count, 3)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [2, 4])

    def test_incomplete_response_is_downloaded_again(self):
        response = MagicMock()
        response.__enter__.return_value.read.side_effect = IncompleteRead(b"partial")
        with patch.object(sync_sheet, "urlopen", side_effect=[response, io.BytesIO(b"complete")]):
            with patch.object(sync_sheet, "sleep"):
                self.assertEqual(sync_sheet.download("https://example.test", "Test source"), b"complete")

    def test_temporary_server_errors_are_retried(self):
        for status in (408, 429, 500, 502, 503, 504):
            with self.subTest(status=status):
                error = HTTPError("https://example.test", status, "Temporary error", {}, None)
                with patch.object(sync_sheet, "urlopen", side_effect=[error, io.BytesIO(b"ok")]):
                    with patch.object(sync_sheet, "sleep"):
                        self.assertEqual(sync_sheet.download("https://example.test", "Test source"), b"ok")

    def test_permanent_http_errors_are_not_retried(self):
        for status in (400, 401, 403, 404):
            with self.subTest(status=status):
                error = HTTPError("https://example.test", status, "Permanent error", {}, None)
                with patch.object(sync_sheet, "urlopen", side_effect=error) as fetch:
                    with patch.object(sync_sheet, "sleep") as sleep:
                        with self.assertRaises(HTTPError):
                            sync_sheet.download("https://example.test", "Test source")
                self.assertEqual(fetch.call_count, 1)
                sleep.assert_not_called()

    def test_exhausted_retries_stop_refresh_without_saving(self):
        with patch.object(sync_sheet, "urlopen", side_effect=URLError("DNS unavailable")) as fetch:
            with patch.object(sync_sheet, "sleep") as sleep:
                with patch.object(sync_sheet, "save_snapshot") as save:
                    with patch.dict(sync_sheet.os.environ, {"LUCRA_WAREHOUSE_SHEET_ID": "test-file"}):
                        with patch.object(sync_sheet.sys, "argv", ["sync_sheet.py", "--link-shared"]):
                            with self.assertRaises(SystemExit) as error:
                                sync_sheet.main()
        self.assertEqual(error.exception.code, 1)
        self.assertEqual(fetch.call_count, 4)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [2, 4, 8])
        save.assert_not_called()

    def test_office_export_still_falls_back_on_http_400(self):
        error = HTTPError("https://example.test", 400, "Office workbook", {}, None)
        with patch.object(sync_sheet, "urlopen", side_effect=error):
            with patch.object(sync_sheet, "read_link_shared_workbook", return_value=[["C8", "6140-1"]]) as workbook:
                with patch.dict(sync_sheet.os.environ, {"LUCRA_WAREHOUSE_SHEET_ID": "test-file"}):
                    self.assertEqual(sync_sheet.read_link_shared_sheet(), [["C8", "6140-1"]])
        workbook.assert_called_once_with("test-file")


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
