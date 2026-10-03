import os
import sys
import logging
import pandas as pd
import re
import time


LOG_DIR = ".logs"
LOG_FILE = "push_contracts.log"
INPUT_DIR = "data"
INPUT_FILE = "spotrac_contracts.csv"


base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

os.makedirs(LOG_DIR, exist_ok=True)
log_path = os.path.join(LOG_DIR, LOG_FILE)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_path, mode="a", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

os.makedirs(INPUT_DIR, exist_ok=True)
input_path = os.path.join(INPUT_DIR, INPUT_FILE)

from utils.sheets_manager import GoogleSheetsManager


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

def update_sheets(df: pd.DataFrame, sheet_name: str, data_range: str) -> None:
        logging.info(f"Updating Google Sheets: {sheet_name}")
        try:
            # Generate a timestamp for logging and data tracking
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

            # Initialize the Google Sheets manager and clear the target range
            sheets_manager = GoogleSheetsManager()
            sheets_manager.clear_range(sheet_name=sheet_name, range_to_clear=data_range)

            # Exclude the Owner column from the sheet write so it does not overwrite column M
            write_df = df.drop(columns=["Owner"]) if "Owner" in df.columns else df.copy()

            # Write the processed data frame to the sheet starting from cell A1
            sheets_manager.write_data([write_df.columns.tolist()] + write_df.values.tolist(), sheet_name=sheet_name, start_cell="A1")
            logging.info("Google Sheets updated successfully.")

            # Write the timestamp to Google Sheets
            sheets_manager.write_data([[f"{timestamp}"]], sheet_name=sheet_name, start_cell="AB2")
            logging.info("Wrote timestamp to Google Sheets.")
        except Exception as e:
            logging.error(f"Failed to update Google Sheets: {e}")

def main():
    contracts = load_contracts(input_path)
    data = process_data(contracts)
    update_sheets(data, sheet_name="Contracts", data_range="A1:L751")


if __name__ == "__main__":
    logging.info(f"Script execution started: {__file__}")
    main()
    logging.info(f"Script execution completed: {__file__}")
