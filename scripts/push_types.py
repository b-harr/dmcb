import logging
import os
import sys
import time

import pandas as pd

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from scripts.utils import GoogleSheetsManager

LOG_DIR = os.path.join(".logs")
DATA_DIR = os.path.join("data")
LOG_FILE = "push_types.log"
INPUT_FILE = "contract_types.csv"

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

log_path = os.path.join(LOG_DIR, LOG_FILE)
input_path = os.path.join(DATA_DIR, INPUT_FILE)

logging.basicConfig(
    force=True,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_path, mode="a", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)


def load_contract_types(input_csv: str) -> pd.DataFrame:
    if not os.path.exists(input_csv):
        logging.warning("Input CSV file does not exist: %s", input_csv)
        return pd.DataFrame()
    try:
        df = pd.read_csv(input_csv)
        logging.info("Loaded contract types data from %s.", input_csv)
        return df
    except Exception as error:
        logging.error("Failed to load contract types data from CSV: %s", error)
        return pd.DataFrame()


def update_sheets(df: pd.DataFrame, sheet: str) -> None:
    if df.empty:
        logging.warning("No contract types data provided; Google Sheets was not changed.")
        return

    try:
        sheets_manager = GoogleSheetsManager()
        sheets_manager.clear_range(sheet_name=sheet, range_to_clear="A:E")

        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        sheets_manager.write_data(
            [[f"Last updated {timestamp} by {sheets_manager.service_account_email}"]],
            sheet_name=sheet,
            start_cell="A1",
        )
        sheets_manager.write_data(
            [df.columns.tolist()] + df.fillna("").values.tolist(),
            sheet_name=sheet,
            start_cell="A2",
        )
        logging.info("Google Sheets '%s' updated successfully.", sheet)
    except Exception as error:
        logging.error("Failed to update Google Sheets: %s", error)


def main() -> None:
    contract_types = load_contract_types(input_path)
    update_sheets(contract_types, "Contract Types")


if __name__ == "__main__":
    logging.info("Script execution started: %s", __file__)
    main()
    logging.info("Script execution completed: %s", __file__)