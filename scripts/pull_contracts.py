import os
import sys
import logging
import argparse
import re
import pandas as pd
import time


log_file = os.path.join("logs", "get_contracts.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file, mode="a", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

OUTPUT_DIR = "data"
OUTPUT_FILE = "spotrac_contracts.csv"
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_CSV = os.path.join(OUTPUT_DIR, OUTPUT_FILE)

from utils.spotrac_scraper import scrape_all_teams
from utils.text_formatter import make_player_key, make_title_case
from utils.sheets_manager import GoogleSheetsManager


def scrape_all() -> pd.DataFrame | None:
    logging.info("Starting to scrape team contracts from Spotrac...")
    try:
        df = scrape_all_teams()
        if df is None or df.empty:
            logging.warning("No data was returned from the scrape.")
            return None
        return df
    except Exception as e:
        logging.error(f"Scrape failed: {e}")
        return None

def process_data(df: pd.DataFrame) -> pd.DataFrame:
    logging.info("Starting to process scraped contract data...")
    if df is None or df.empty:
        logging.warning("No data provided to process.")
        return pd.DataFrame()

    try:
        # Exclude rows where Player is "Incomplete Roster Charge"
        df = df[df["Player"] != "Incomplete Roster Charge"]

        # Add derived columns for Player Key and Team Link
        df["Player Key"] = df["Player"].apply(make_player_key)
        df["Team Link"] = df["Team"].apply(lambda team: f"https://www.spotrac.com/nba/{team}/yearly")
        
        # Format, sort, and reorder columns
        df["Team"] = df["Team"].apply(make_title_case)
        df = df.sort_values(by=["Player Key", "Team"], ignore_index=True)
        required_columns = ["Player", "Player Link", "Player Key", "Team", "Team Link", "Position", "Age"]
        dynamic_columns = [col for col in df.columns if col.startswith("20")]
        column_order = required_columns + dynamic_columns
        
        return df[column_order]
    except Exception as e:
        logging.error(f"Data processing failed: {e}")
        return pd.DataFrame()

def get_owner(df: pd.DataFrame, sheet_name="Contracts") -> pd.DataFrame:
    try:
        sheets_manager = GoogleSheetsManager()
        raw_data = sheets_manager.read_data(sheet_name=sheet_name)
    except Exception as e:
        logging.warning(f"Could not read owner data from Google Sheets '{sheet_name}': {e}")
        return df

    if not raw_data:
        return df

    header = raw_data[0]
    rows = raw_data[1:] if len(raw_data) > 1 else []

    if len(header) <= 16:
        logging.warning("Google Sheets 'Contracts' tab does not contain the expected owner column (Q).")
        return df

    owner_df = pd.DataFrame(rows, columns=[str(col).strip() for col in header])
    owner_df = owner_df.iloc[:, [0, 1, 2, 16]].copy()
    owner_df.columns = ["Player", "Player Link", "Player Key", "Owner"]

    owner_df["Player Key"] = owner_df["Player Key"].astype(str).str.strip()
    owner_df = owner_df.dropna(subset=["Player Key"])
    owner_df = owner_df[owner_df["Player Key"] != ""]

    owner_lookup = {}
    for _, row in owner_df.iterrows():
        key = row["Player Key"]
        owner = row["Owner"]
        owner_lookup.setdefault(key, owner)

    if df.empty:
        return df

    merged_df = df.copy()
    merged_df["Player Key"] = merged_df["Player Key"].astype(str).str.strip()
    merged_df["Owner"] = merged_df["Player Key"].map(owner_lookup)
    merged_df["Owner"] = merged_df["Owner"].replace({None: ""}).fillna("")

    other_columns = [col for col in merged_df.columns if col != "Owner"]
    
    return merged_df[other_columns + ["Owner"]]

def add_owner(df: pd.DataFrame) -> pd.DataFrame:
    logging.info("Adding Owner column to the DataFrame...")
    if df is None or df.empty:
        logging.warning("No data provided to add Owner column.")
        return pd.DataFrame()

    try:
        return get_owner(df, sheet_name="Contracts")
    except Exception as e:
        logging.error(f"Failed to add Owner column: {e}")
        return pd.DataFrame()

def save_data(df: pd.DataFrame, output_csv: str) -> None:
    logging.info(f"Saving data to CSV: {output_csv}")

    if df is None or df.empty:
        logging.warning("No data provided to save.")
        return

    try:
        df.to_csv(output_csv, index=False)
        logging.info(f"Data saved successfully to {output_csv}.")
    except Exception as e:
        logging.error(f"Failed to save data to CSV: {e}")

def main():
    df = scrape_all()
    df = process_data(df)
    df = add_owner(df)
    save_data(df, OUTPUT_CSV)


if __name__ == "__main__":
    logging.info(f"Script execution started: {__file__}")
    main()
    logging.info(f"Script execution completed: {__file__}")
