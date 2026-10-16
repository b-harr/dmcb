import os
import sys
import logging
import pandas as pd

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

from scripts.utils import GoogleSheetsManager

LOG_DIR = os.path.join(".logs")
DATA_DIR = os.path.join("data")
LOG_FILE = "push_stats.log"
INPUT_FILE = "bbref_stats.csv"

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

NUMERIC_COLUMNS = ["PTS", "TRB", "AST", "STL", "BLK", "TOV", "PF", "G", "MP"]


def load_stats(input_csv: str) -> pd.DataFrame:
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

def update_sheets(df: pd.DataFrame, sheet: str) -> None:
    try:
        sheets_manager = GoogleSheetsManager()
        sheets_manager.clear_data(sheet)
        logging.info(f"Cleared existing data in Google Sheets: {sheet}")

        timestamp = logging.Formatter('%(asctime)s').format(logging.LogRecord("", 0, "", 0, "", [], None))
        sheets_manager.write_data([[f"Last updated {timestamp} by {sheets_manager.service_account_email} from {os.path.basename(__file__)}"]], sheet, cell="A1")
        logging.info("Added timestamp to Google Sheets.")

        write_df = df.replace([pd.NA, None, float("inf"), float("-inf")], "").fillna("")
        sheets_manager.write_data([write_df.columns.tolist()] + write_df.values.tolist(), sheet, cell="A2")
        logging.info(f"Data successfully written to Google Sheets: {sheet}")
    except Exception as e:
        logging.error(f"Error updating Google Sheets: {e}")

def main():
    df = load_stats(input_path)
    update_sheets(df, "Stats")
    print(df)


if __name__ == "__main__":
    logging.info(f"Script execution started: {__file__}")
    main()
    logging.info(f"Script execution completed: {__file__}")
