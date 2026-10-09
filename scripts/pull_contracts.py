import os
import sys
import logging
import pandas as pd

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

from utils.text_formatter import make_player_key, make_title_case
from utils.spotrac_scraper import scrape_teams
from utils.sheets_manager import GoogleSheetsManager

LOG_DIR = os.path.join(".logs")
DATA_DIR = os.path.join("data")
LOG_FILE = "pull_contracts.log"
OUTPUT_FILE = "spotrac_contracts.csv"

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


def scrape_all() -> pd.DataFrame | None:
    logging.info("Starting to scrape team contracts from Spotrac...")
    try:
        df = scrape_teams()
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

        logging.info("Processed and formatted contract data.")
        return df[column_order]
    except Exception as e:
        logging.error(f"Data processing failed: {e}")
        return pd.DataFrame()

def get_owners(sheet_name="Contracts") -> pd.DataFrame:
    try:
        sheets_manager = GoogleSheetsManager()
        raw_data = sheets_manager.read_data(sheet_name=sheet_name)
    except Exception as e:
        logging.warning(f"Could not read owner data from Google Sheets '{sheet_name}': {e}")
        return pd.DataFrame(columns=["Player", "Player Link", "Player Key", "Owner"])

    if not raw_data:
        return pd.DataFrame(columns=["Player", "Player Link", "Player Key", "Owner"])

    header = raw_data[0]
    rows = raw_data[1:] if len(raw_data) > 1 else []

    if len(header) <= 16:
        logging.warning("Google Sheets 'Contracts' tab does not contain the expected owner column (Q).")
        return pd.DataFrame(columns=["Player", "Player Link", "Player Key", "Owner"])

    owner_df = pd.DataFrame(rows, columns=[str(col).strip() for col in header])
    owner_df = owner_df.iloc[:, [0, 1, 2, 16]].copy()
    owner_df.columns = ["Player", "Player Link", "Player Key", "Owner"]
    return owner_df

def merge_owners(contracts: pd.DataFrame, owners: pd.DataFrame) -> pd.DataFrame:
    if contracts.empty:
        logging.info("Contracts DataFrame is empty, returning as is.")
        return contracts

    merged_df = contracts.copy()
    if "Player Key" in merged_df.columns and "Player Key" in owners.columns and "Owner" in owners.columns:
        owner_data = owners[["Player Key", "Owner"]].copy()
        owner_data["Player Key"] = owner_data["Player Key"].astype("string").str.strip()
        owner_data = owner_data.dropna(subset=["Player Key"])
        owner_data = owner_data[owner_data["Player Key"] != ""]
        owner_lookup = owner_data.drop_duplicates("Player Key", keep="first").set_index("Player Key")["Owner"]

        merged_df["Player Key"] = merged_df["Player Key"].astype("string").str.strip()
        merged_df["Owner"] = merged_df["Player Key"].map(owner_lookup).fillna("")
        logging.info("Merged owner data into contracts DataFrame.")
    else:
        merged_df["Owner"] = ""

    other_columns = [col for col in merged_df.columns if col != "Owner"]
    return merged_df[other_columns + ["Owner"]]

def save_data(df: pd.DataFrame, output_csv: str) -> None:
    if df is None or df.empty:
        logging.warning("No data provided to save.")
        return
    try:
        df.to_csv(output_csv, index=False)
        logging.info(f"Data saved successfully to {output_csv}.")
    except Exception as e:
        logging.error(f"Failed to save data to CSV: {e}")

def main():
    contracts = scrape_all()
    contracts = process_data(contracts)
    owners = get_owners(sheet_name="Contracts")
    data = merge_owners(contracts, owners)
    save_data(data, output_path)


if __name__ == "__main__":
    logging.info(f"Script execution started: {__file__}")
    main()
    logging.info(f"Script execution completed: {__file__}")
