import os
import sys
import logging
import requests
import json
from bs4 import BeautifulSoup
import pandas as pd

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

from utils.text_formatter import make_player_key
from utils.spotrac_scraper import scrape_player

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

def scrape_player_url(url: str) -> BeautifulSoup:
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    return BeautifulSoup(response.text, "html.parser")

def scrape_player_details(soup: BeautifulSoup) -> pd.DataFrame:
    details = {}

    for script in soup.select('script[type="application/ld+json"]'):
        try:
            structured_data = json.loads(script.string or script.get_text())
        except json.JSONDecodeError:
            continue

        if structured_data.get("@type") == "Person":
            details["Player"] = structured_data.get("name")
            details["Link"] = structured_data.get("url")
            break

    profile = soup.select_one("#main article > div.row.m-0.mt-0.pb-3")
    if profile is not None:
        team_position = profile.select_one(".col-md-12.text-yellow.fw-bold span")
        if team_position is not None:
            team_link = team_position.find("a")
            if team_link is not None:
                team = team_link.get_text(strip=True)
                details["Team"] = team
                details["Position"] = team_position.get_text(" ", strip=True).replace(team, "", 1).strip(" ,")

        for label in profile.find_all("strong"):
            value = label.find_next_sibling("span")
            if value is not None:
                details[label.get_text(strip=True).rstrip(":")] = value.get_text(" ", strip=True)

    table = soup.find("div", class_="contract-details")
    if table is not None:
        for label, value in zip(
            table.find_all("div", class_="label"),
            table.find_all("div", class_="value"),
        ):
            details[label.get_text(strip=True).rstrip(":")] = value.get_text(strip=True)

    return pd.DataFrame([details])

def scrape_player(url: str) -> pd.DataFrame:
    soup = scrape_player_url(url)
    df = scrape_player_details(soup)
    df["Key"] = df["Player"].apply(make_player_key)
    return df

def scrape_players(urls: list[str]) -> pd.DataFrame:
    all_details = []
    for url in urls:
        logging.info(f"Scraping player details from URL: {url}")
        details = scrape_player(url)
        all_details.append(details)
    return pd.concat(all_details, ignore_index=True)

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

def scrape_players_with_retries(urls: list[str]) -> pd.DataFrame:
    all_details = []
    for url in urls:
        for attempt in range(MAX_RETRIES):
            try:
                details = scrape_players(url)
                all_details.append(details)
                break
            except Exception as e:
                print(f"Attempt {attempt + 1} failed for URL {url}: {e}")
                if attempt == MAX_RETRIES - 1:
                    raise
    return pd.concat(all_details, ignore_index=True)

def main():
    df = get_players_from_csv(input_path)
    df = filter_active_players(df)
    urls = return_player_urls_to_scrape(df)
    details = scrape_players(urls)
    details = select_columns(details)
    print(details.to_string())


if __name__ == "__main__":
    main()
