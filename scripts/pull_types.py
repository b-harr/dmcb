import os
import sys
import logging
import pandas as pd

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

LOG_DIR = ".logs"
LOG_FILE = "pull_types.log"
INPUT_DIR = "data"
INPUT_FILE = "spotrac_contracts.csv"
OUTPUT_DIR = "data"
OUTPUT_FILE = "contract_types.csv"

os.makedirs(LOG_DIR, exist_ok=True)
log_path = os.path.join(LOG_DIR, LOG_FILE)
os.makedirs(INPUT_DIR, exist_ok=True)
input_path = os.path.join(INPUT_DIR, INPUT_FILE)
os.makedirs(OUTPUT_DIR, exist_ok=True)
output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILE)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_path, mode="a", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

from utils.sheets_manager import GoogleSheetsManager
from utils.spotrac_scraper import scrape_player_details
from utils.text_formatter import make_title_case


def get_links_to_scrape(unique_links, output_csv_path):
    if not os.path.exists(output_csv_path):
        return unique_links

    existing_df = pd.read_csv(output_csv_path)
    missing_cols = ["Signed Using", "Drafted"]

    if set(missing_cols).issubset(existing_df.columns):
        missing_mask = (
            existing_df[missing_cols].isna().all(axis=1)
            | existing_df[missing_cols].eq("").all(axis=1)
        )

        if missing_mask.any():
            missing_links = set(
                existing_df.loc[missing_mask, "Player Link"].dropna().astype(str)
            )
            cleaned_df = existing_df.loc[~missing_mask].copy()
            cleaned_df.to_csv(output_csv_path, index=False)
            logging.info(f"Removed {missing_mask.sum()} rows with missing contract metadata from {output_csv_path}")
        else:
            missing_links = set()
            cleaned_df = existing_df
    else:
        missing_links = set()
        cleaned_df = existing_df

    existing_links = set(cleaned_df["Player Link"].dropna().astype(str))

    return [link for link in unique_links if link in missing_links or link not in existing_links]