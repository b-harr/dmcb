import os
import sys
import logging
import pandas as pd

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

from scripts.utils import scrape_players

LOG_DIR = os.path.join(".logs")
LOG_FILE = "pull_details.log"
DATA_DIR = os.path.join("data")
INPUT_FILE = "spotrac_contracts.csv"
OUTPUT_FILE = "contract_details.csv"

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

log_path = os.path.join(LOG_DIR, LOG_FILE)
input_path = os.path.join(DATA_DIR, INPUT_FILE)
output_path = os.path.join(DATA_DIR, OUTPUT_FILE)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_path, mode="a", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/26.6.2 Safari/605.1.15"
    )
}
MAX_RETRIES = 3
RETRY_DELAY = 2
TIMEOUT = 10


def get_players_from_csv(input_path: str) -> list[str]:
    try:
        return pd.read_csv(input_path)
    except Exception as e:
        logging.error(f"Error reading {input_path}: {e}")
        return []

def filter_active_players(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        logging.warning("The DataFrame is empty. No active players to filter.")
        return df
    try:
        active_players = df[
            (df["Player"] != "Two-Way") &
            (df["Player"] != "-")
        ]
        return active_players
    except KeyError as e:
        logging.error(f"Missing expected column in DataFrame: {e}")
        return pd.DataFrame()

def get_player_urls_to_scrape(df: pd.DataFrame) -> list[str]:
    missing_columns = ["Signed Using", "Drafted"]

    if set(missing_columns).issubset(df.columns):
        missing_mask = (
            df[missing_columns].isna().all(axis=1) |
            df[missing_columns].eq("").all(axis=1)
        )

        if missing_mask.any():
            missing_urls = set(
                df.loc[missing_mask, "Player Link"].dropna().astype(str)
            )
            cleaned_df = df.loc[~missing_mask, "Player Link"].dropna().astype(str)
        else:
            missing_urls = set()
            cleaned_df = df
    else:
        logging.warning(f"Missing expected columns in DataFrame: {missing_columns}")
        missing_urls = set()
        cleaned_df = df

    existing_urls = set(cleaned_df["Player Link"].dropna().astype(str))

    for link in existing_urls:
        if link in missing_urls:
            logging.info(f"Player link '{link}' already exists in the DataFrame. Skipping scraping.")
            missing_urls.discard(link)

def return_player_urls_to_scrape(df: pd.DataFrame) -> list[str]:
    if df.empty:
        logging.warning("The DataFrame is empty. No player URLs to return.")
        return []
    try:
        urls = df["Player Link"].dropna().unique().tolist()
        return urls
    except KeyError as e:
        logging.error(f"Missing expected column in DataFrame: {e}")
        return []

def select_columns(df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "Player",
        "Link",
        "Key",
        "Drafted",
        "Signed Using",
        "College"
    ]
    details = df[columns]
    return details

def main():
    df = get_players_from_csv(input_path)
    df = filter_active_players(df)
    urls = return_player_urls_to_scrape(df)
    details = scrape_players(urls)
    details = select_columns(details)
    print(details)


if __name__ == "__main__":
    main()
