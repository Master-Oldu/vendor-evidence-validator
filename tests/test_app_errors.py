import io
import unittest
from pathlib import Path

from app import app


UPLOAD_FOLDER = Path("uploads")


class AppErrorTests(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()


    def test_missing_questionnaire_returns_400(self):
        response = self.client.post(
            "/",
            data={},
            content_type="multipart/form-data",
        )

        text = response.get_data(
            as_text=True
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "A questionnaire file is required.",
            text,
        )


    def test_missing_evidence_returns_400(self):
        response = self.client.post(
            "/",
            data={
                "questionnaire": (
                    io.BytesIO(b"test"),
                    "test.xlsx",
                ),
            },
            content_type="multipart/form-data",
        )

        text = response.get_data(
            as_text=True
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "At least one evidence file is required.",
            text,
        )


    def test_missing_questionnaire_file_returns_404(self):
        response = self.client.post(
            "/select-sheets",
            data={
                "questionnaire_name": (
                    "does-not-exist.xlsx"
                ),
                "selected_sheets": "Sheet1",
            },
        )

        text = response.get_data(
            as_text=True
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertIn(
            "The questionnaire file could not be found.",
            text,
        )


    def test_no_worksheet_selected_returns_400(self):
        test_file = (
            UPLOAD_FOLDER
            / "day10-test-questionnaire.xlsx"
        )

        test_file.write_bytes(
            b"temporary test file"
        )

        try:
            response = self.client.post(
                "/select-sheets",
                data={
                    "questionnaire_name": (
                        test_file.name
                    ),
                },
            )

            text = response.get_data(
                as_text=True
            )

            self.assertEqual(
                response.status_code,
                400,
            )

            self.assertIn(
                "Select at least one worksheet.",
                text,
            )

        finally:
            test_file.unlink(
                missing_ok=True
            )


    def test_invalid_sheet_count_returns_400(self):
        test_file = (
            UPLOAD_FOLDER
            / "day10-test-questionnaire.xlsx"
        )

        test_file.write_bytes(
            b"temporary test file"
        )

        try:
            response = self.client.post(
                "/map-selected-sheets",
                data={
                    "questionnaire_name": (
                        test_file.name
                    ),
                    "validation_start": "1",
                    "validation_limit": "1",
                    "sheet_count": "abc",
                },
            )

            text = response.get_data(
                as_text=True
            )

            self.assertEqual(
                response.status_code,
                400,
            )

            self.assertIn(
                "Worksheet count is invalid.",
                text,
            )

        finally:
            test_file.unlink(
                missing_ok=True
            )


if __name__ == "__main__":
    unittest.main()