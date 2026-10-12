import os
import sys
import logging
import pandas as pd

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

from utils import scrape_positions, merge_owners

LOG_DIR = os.path.join(".logs")
DATA_DIR = os.path.join("data")
LOG_FILE = "pull_positions.log"
OUTPUT_FILE = "sportsws_positions.csv"

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

log_path = os.path.join(LOG_DIR, LOG_FILE)
output_path = os.path.join(DATA_DIR, OUTPUT_FILE)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_path, mode="a", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)


def scrape_sportsws_positions() -> pd.DataFrame:
    return scrape_positions()

def merge_fantasy_owners(df: pd.DataFrame) -> pd.DataFrame:
    return merge_owners(df)

def save_positions_data(df: pd.DataFrame, output_csv: str) -> None:
    if df is None or df.empty:
        logging.warning("No data provided to save.")
        return
    try:
        df.to_csv(output_csv, index=False)
        logging.info(f"Data saved successfully to {output_csv}.")
    except Exception as e:
        logging.error(f"Failed to save data to CSV: {e}")

def main():
    positions = scrape_sportsws_positions()
    data = merge_fantasy_owners(positions)
    save_positions_data(data, output_path)
    print(data)


if __name__ == "__main__":
    main()
