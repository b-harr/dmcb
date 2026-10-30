from __future__ import annotations

import csv
from datetime import datetime
import json
import logging
import os
from pathlib import Path
from typing import Any

import gspread
import pandas as pd
from dotenv import load_dotenv

from dmcb.models.records import SheetWritePlan


class GoogleSheetsService:
    def __init__(
        self,
        credentials_path: str | Path | None = None,
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

            path = Path(credentials_path).expanduser()
            if not path.is_file():
                raise FileNotFoundError(f"Google credentials file not found: {path}")

            logging.info("Initializing GoogleSheetsService...")
            self.gc = gspread.service_account(filename=str(path))
            self.sheet = self.gc.open_by_url(spreadsheet_url)

            with path.open(encoding="utf-8") as file:
                credentials = json.load(file)
                self.service_account_email = credentials.get("client_email")

            logging.info(
                "Successfully connected to Google Sheets. Service Account Email: %s",
                self.service_account_email,
            )
        except Exception:
            logging.exception("Failed to initialize GoogleSheetsService")
            raise

    def get_worksheet(self, sheet: str):
        try:
            worksheet = self.sheet.worksheet(sheet)
            logging.info("Accessed worksheet: %s", sheet)
            return worksheet
        except Exception:
            logging.exception("Error accessing worksheet %r", sheet)
            raise

    def read_data(self, sheet: str) -> list[list[str]]:
        try:
            data = self.get_worksheet(sheet).get_all_values()
            logging.info("Read %s rows from worksheet %r.", len(data), sheet)
            return data
        except Exception:
            logging.exception("Error reading data from worksheet %r", sheet)
            raise

    def read_values(self, worksheet_name: str) -> list[list[str]]:
        return self.read_data(worksheet_name)

    def write_data(
        self,
        data: Any,
        sheet: str | None = None,
        cell: str | None = None,
        *,
        sheet_name: str | None = None,
        start_cell: str | None = None,
    ) -> None:
        target_sheet = sheet or sheet_name
        target_cell = cell or start_cell
        if not target_sheet:
            raise ValueError("A worksheet name is required.")
        if not target_cell:
            raise ValueError("A starting cell is required.")
        try:
            self.get_worksheet(target_sheet).update(target_cell, data)
            logging.info(
                "Written data to worksheet %r starting at %r.",
                target_sheet,
                target_cell,
            )
        except Exception:
            logging.exception("Error writing data to worksheet %r", target_sheet)
            raise

    def clear_data(self, sheet: str) -> None:
        try:
            self.get_worksheet(sheet).clear()
            logging.info("Cleared data from worksheet %r.", sheet)
        except Exception:
            logging.exception("Error clearing data in worksheet %r", sheet)
            raise

    def clear_range(
        self,
        sheet: str | None = None,
        range: str | None = None,
        *,
        sheet_name: str | None = None,
        range_to_clear: str | None = None,
    ) -> None:
        target_sheet = sheet or sheet_name
        target_range = range or range_to_clear
        if not target_sheet:
            raise ValueError("A worksheet name is required.")
        if not target_range:
            raise ValueError("A range to clear is required.")
        try:
            self.get_worksheet(target_sheet).batch_clear([target_range])
            logging.info(
                "Cleared range %r in worksheet %r", target_range, target_sheet
            )
        except Exception:
            logging.exception(
                "Error clearing range %r in worksheet %r",
                target_range,
                target_sheet,
            )
            raise

    def read_owners(self) -> pd.DataFrame:
        from dmcb.utils import make_player_key

        values = self.read_values("Owned")
        columns = ["Player", "Player Key", "Owner", "Sheet Row"]
        if len(values) < 2:
            return pd.DataFrame(columns=columns)

        owners = []
        for row_number, row in enumerate(values[1:], start=2):
            owner = row[0].strip() if len(row) > 0 else ""
            player = row[3].strip() if len(row) > 3 else ""
            key = make_player_key(player) if player else ""
            if key:
                owners.append(
                    {
                        "Player": player,
                        "Player Key": key,
                        "Owner": owner,
                        "Sheet Row": row_number,
                    }
                )
        return pd.DataFrame(owners, columns=columns)

    def read_contracts(self) -> tuple[list[list[str]], pd.DataFrame]:
        from dmcb.utils import make_player_key

        values = self.read_values("Contracts")
        if not values:
            return values, pd.DataFrame()
        headers = [str(value).strip() for value in values[0]]
        if "Player Key" not in headers:
            raise ValueError("The Contracts worksheet is missing the 'Player Key' header.")
        records = []
        for row_number, row in enumerate(values[1:], start=2):
            expanded = list(row) + [""] * max(0, len(headers) - len(row))
            record = dict(zip(headers, expanded))
            record["Sheet Row"] = row_number
            if not str(record.get("Player Key", "")).strip() and record.get("Player"):
                record["Player Key"] = make_player_key(str(record["Player"]))
            if str(record.get("Player Key", "")).strip():
                records.append(record)
        return values, pd.DataFrame(records)

    def build_write_plan(
        self, spotrac: pd.DataFrame, owners: pd.DataFrame
    ) -> tuple[list[list[str]], SheetWritePlan]:
        from dmcb.services.reconciliation import build_sheet_write_plan

        values = self.read_values("Contracts")
        return values, build_sheet_write_plan(spotrac, values, owners)

    @staticmethod
    def save_backup(values: list[list[str]], backup_directory: str | Path) -> Path:
        directory = Path(backup_directory).expanduser()
        directory.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        destination = directory / f"contracts-{timestamp}.csv"
        with destination.open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerows(values)
        return destination

    def apply_write_plan(
        self,
        plan: SheetWritePlan,
        expected_sheet_values: list[list[str]] | None = None,
    ) -> None:
        worksheet = self.get_worksheet("Contracts")
        current_values = worksheet.get_all_values()
        if expected_sheet_values is not None and current_values != expected_sheet_values:
            raise RuntimeError(
                "The Contracts worksheet changed after the write preview. "
                "Reload the sheet and review a fresh preview before writing."
            )
        requests = [
            {"range": update.cell, "values": [[update.value]]}
            for update in plan.updates
        ]
        if plan.append_rows:
            if plan.append_start_row is None:
                raise ValueError("The write plan is missing the new-row start position.")
            requests.extend(
                {
                    "range": f"A{plan.append_start_row + offset}:M{plan.append_start_row + offset}",
                    "values": [row],
                }
                for offset, row in enumerate(plan.append_rows)
            )
        if requests:
            worksheet.batch_update(requests, value_input_option="RAW")


GoogleSheetsManager = GoogleSheetsService
