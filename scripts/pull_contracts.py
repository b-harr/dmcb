import os
import sys
import logging
import pandas as pd

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

from scripts.utils import make_player_key, make_title_case, scrape_teams, GoogleSheetsManager, save_owned, scrape_owners

LOG_DIR = os.path.join(".logs")
DATA_DIR = os.path.join("data")
LOG_FILE = "pull_contracts.log"
OUTPUT_FILE = "spotrac_contracts.csv"
OWNED_OUTPUT_FILE = "owned_contracts.csv"

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

log_path = os.path.join(LOG_DIR, LOG_FILE)
output_path = os.path.join(DATA_DIR, OUTPUT_FILE)
owned_output_path = os.path.join(DATA_DIR, OWNED_OUTPUT_FILE)

logging.basicConfig(
    force=True,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_path, mode="a", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)


def scrape_all() -> pd.DataFrame:
    logging.info("Starting to scrape team contracts from Spotrac...")
    try:
        df = scrape_teams()
        if df is None or df.empty:
            raise RuntimeError("Spotrac returned no contract data")
        return df
    except Exception as e:
        logging.exception("Failed to scrape contracts from Spotrac")
        raise RuntimeError("Failed to scrape contracts from Spotrac") from e

def process_data(df: pd.DataFrame) -> pd.DataFrame:
    logging.info("Starting to process scraped contract data...")
    if df is None or df.empty:
        raise ValueError("No contract data provided to process")
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
        logging.exception("Failed to process contract data")
        raise RuntimeError("Failed to process contract data") from e

def update_owners():
    sheet = "Owned"
    output = os.path.join("data", "dmcb_owners.csv")
    df = scrape_owners(sheet, output)
    column_order = ["Player", "Player Key", "Owner"]
    df = df[column_order].sort_values("Player Key")
    df.to_csv(output, index=False)

def get_owners(sheet="Contracts") -> pd.DataFrame:
    try:
        sheets_manager = GoogleSheetsManager()
        raw_data = sheets_manager.read_data(sheet=sheet)
    except Exception as e:
        logging.exception("Could not read owner data from Google Sheets '%s'", sheet)
        raise RuntimeError(f"Could not read owner data from Google Sheets '{sheet}'") from e

    if not raw_data:
        raise ValueError(f"Google Sheets '{sheet}' contains no owner data")

    header = raw_data[0]
    rows = raw_data[1:] if len(raw_data) > 1 else []

    if len(header) <= 16:
        raise ValueError(f"Google Sheets '{sheet}' does not contain the expected owner column (Q)")

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
        from dmcb.services.reconciliation import owner_index

        owner_lookup, ambiguous_keys = owner_index(owners)
        if ambiguous_keys:
            logging.warning(
                "Skipped owner assignments for ambiguous Player Key(s): %s",
                ", ".join(sorted(ambiguous_keys)),
            )
        merged_df["Player Key"] = merged_df["Player Key"].astype("string").str.strip()
        merged_df["Owner"] = merged_df["Player Key"].map(owner_lookup).fillna("")
        logging.info("Merged owner data into contracts DataFrame.")
    else:
        merged_df["Owner"] = ""

    other_columns = [col for col in merged_df.columns if col != "Owner"]
    return merged_df[other_columns + ["Owner"]]

def save_data(df: pd.DataFrame, output_csv: str) -> None:
    if df is None or df.empty:
        raise ValueError(f"Refusing to save empty contracts data to {output_csv}")
    try:
        df.to_csv(output_csv, index=False)
        logging.info(f"Data saved successfully to {output_csv}.")
    except Exception as e:
        logging.exception("Failed to save contracts data to %s", output_csv)
        raise RuntimeError(f"Failed to save contracts data to {output_csv}") from e

def main():
    update_owners()
    contracts = scrape_all()
    contracts = process_data(contracts)
    owners = get_owners(sheet="Contracts")
    data = merge_owners(contracts, owners)
    save_data(data, output_path)
    save_owned(data, owned_output_path)


if __name__ == "__main__":
    logging.info(f"Script execution started: {__file__}")
    main()
    logging.info(f"Script execution completed: {__file__}")
