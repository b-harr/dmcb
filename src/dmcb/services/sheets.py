from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

import pandas as pd

from dmcb.models.records import SheetWritePlan
from dmcb.services.reconciliation import build_sheet_write_plan
from scripts.utils import GoogleSheetsManager, make_player_key


class GoogleSheetsService:
    def __init__(self, credentials_path: str | Path, spreadsheet_url: str):
        path = Path(credentials_path).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"Google credentials file not found: {path}")
        if not spreadsheet_url.strip():
            raise ValueError("Google Sheets spreadsheet URL is required.")

        self.manager = GoogleSheetsManager(str(path), spreadsheet_url)
        self.spreadsheet = self.manager.sheet

    def read_values(self, worksheet_name: str) -> list[list[str]]:
        return self.spreadsheet.worksheet(worksheet_name).get_all_values()

    def read_owners(self) -> pd.DataFrame:
        values = self.read_values("Owned")
        if len(values) < 2:
            return pd.DataFrame(columns=["Player", "Player Key", "Owner"])

        owners = []
        for row_number, row in enumerate(values[1:], start=2):
            owner = row[0].strip() if len(row) > 0 else ""
            player = row[3].strip() if len(row) > 3 else ""
            key = make_player_key(player) if player else ""
            if key:
                owners.append(
                    {"Player": player, "Player Key": key, "Owner": owner, "Sheet Row": row_number}
                )
        return pd.DataFrame(owners, columns=["Player", "Player Key", "Owner", "Sheet Row"])

    def read_contracts(self) -> tuple[list[list[str]], pd.DataFrame]:
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
        worksheet = self.spreadsheet.worksheet("Contracts")
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