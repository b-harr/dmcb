from __future__ import annotations

import json
import logging
import os

import gspread
import pandas as pd
from dotenv import load_dotenv


class GoogleSheetsManager:
    def __init__(
        self,
        credentials_path: str | None = None,
        spreadsheet_url: str | None = None,
    ):
        try:
            if not credentials_path or not spreadsheet_url:
                load_dotenv()
            credentials_path = credentials_path or os.getenv("GOOGLE_SHEETS_CREDENTIALS")
            spreadsheet_url = spreadsheet_url or os.getenv("GOOGLE_SHEETS_URL")
            if not credentials_path:
                raise ValueError("Google Sheets credentials path is not configured.")
            if not spreadsheet_url:
                raise ValueError("Google Sheets spreadsheet URL is not configured.")

            logging.info("Initializing GoogleSheetsManager...")
            self.gc = gspread.service_account(filename=credentials_path)
            self.sheet = self.gc.open_by_url(spreadsheet_url)

            with open(credentials_path, encoding="utf-8") as file:
                credentials = json.load(file)
                self.service_account_email = credentials.get("client_email")

            logging.info(
                "Successfully connected to Google Sheets. Service Account Email: %s",
                self.service_account_email,
            )
        except Exception:
            logging.exception("Failed to initialize GoogleSheetsManager")
            raise

    def get_worksheet(self, sheet: str):
        try:
            worksheet = self.sheet.worksheet(sheet)
            logging.info("Accessed worksheet: %s", sheet)
            return worksheet
        except Exception:
            logging.exception("Error accessing worksheet %r", sheet)
            raise

    def read_data(self, sheet: str):
        try:
            worksheet = self.get_worksheet(sheet)
            data = worksheet.get_all_values()
            logging.info("Read %s rows from worksheet %r.", len(data), sheet)
            return data
        except Exception:
            logging.exception("Error reading data from worksheet %r", sheet)
            raise

    def write_data(self, data: pd.DataFrame, sheet: str, cell: str):
        try:
            worksheet = self.get_worksheet(sheet)
            worksheet.update(cell, data)
            logging.info("Written data to worksheet %r starting at %r.", sheet, cell)
        except Exception:
            logging.exception("Error writing data to worksheet %r", sheet)
            raise

    def clear_data(self, sheet: str):
        try:
            worksheet = self.get_worksheet(sheet)
            worksheet.clear()
            logging.info("Cleared data from worksheet %r.", sheet)
        except Exception:
            logging.exception("Error clearing data in worksheet %r", sheet)
            raise

    def clear_range(self, sheet: str, range: str):
        try:
            worksheet = self.get_worksheet(sheet)
            worksheet.batch_clear([range])
            logging.info("Cleared range %r in worksheet %r.", range, sheet)
        except Exception:
            logging.exception(
                "Error clearing range %r in worksheet %r", range, sheet
            )
            raise
