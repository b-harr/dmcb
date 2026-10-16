import os
import sys
import logging
import pandas as pd
import re
import time

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

from scripts.utils import GoogleSheetsManager

LOG_DIR = os.path.join(".logs")
DATA_DIR = os.path.join("data")
LOG_FILE = "push_contracts.log"
INPUT_FILE = "spotrac_contracts.csv"

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
        logging.StreamHandler(sys.stdout)
    ]
)


def load_contracts(input_csv: str) -> pd.DataFrame:
    if not os.path.exists(input_csv):
        logging.warning(f"Input CSV file does not exist: {input_csv}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(input_csv)
        logging.info(f"Loaded contracts data from {input_csv}.")
        return df
    except Exception as e:
        logging.error(f"Failed to load contracts data from CSV: {e}")
        return pd.DataFrame()

def process_data(df: pd.DataFrame) -> pd.DataFrame:
        # Identify salary/year columns (those starting with '20', e.g., '2025-26')
        salary_cols = [col for col in df.columns if re.match(r"20\d{2}-\d{2}", col)]

        # Convert any column like '2025-26' to numeric if it has strings with $
        for col in salary_cols:
            # Remove $ and commas, convert numeric values to float, leave text as-is
            df[col + "_numeric"] = pd.to_numeric(df[col].replace(r'[\$,]', '', regex=True), errors='coerce')
            # Replace numeric values in the original column, leave non-numeric as text
            df[col] = df[col + "_numeric"].combine_first(df[col])
            # Drop temporary numeric helper column
            df.drop(columns=[col + "_numeric"], inplace=True)

        # Clean up before updating Google Sheets
        df = df.replace([pd.NA, None, float("inf"), float("-inf")], "")
        df = df.fillna("")
        return df

def update_sheets(df: pd.DataFrame, sheet: str, range: str) -> None:
        logging.info(f"Updating Google Sheets: {sheet}")
        try:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

            sheets_manager = GoogleSheetsManager()
            sheets_manager.clear_range(sheet, range)

            # Exclude the Owner column from the sheet write so it does not overwrite column M
            write_df = df.drop(columns=["Owner"]) if "Owner" in df.columns else df.copy()

            sheets_manager.write_data([write_df.columns.tolist()] + write_df.values.tolist(), sheet=sheet, cell="A1")
            logging.info("Google Sheets updated successfully.")

            sheets_manager.write_data([[f"{timestamp}"]], sheet, cell="AB2")
            logging.info("Wrote timestamp to Google Sheets.")
        except Exception as e:
            logging.error(f"Failed to update Google Sheets: {e}")

def main():
    contracts = load_contracts(input_path)
    data = process_data(contracts)
    update_sheets(data, sheet="Contracts", range="A1:L751")


if __name__ == "__main__":
    logging.info(f"Script execution started: {__file__}")
    main()
    logging.info(f"Script execution completed: {__file__}")
