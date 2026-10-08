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

LOG_PATH = os.path.join(".logs", "pull_details.log")
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, mode="a", encoding="utf-8"),
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
PLAYERS_TO_SCRAPE = [
    "https://www.spotrac.com/nba/player/_/id/8067/nikola-vucevic",
    "https://www.spotrac.com/nba/player/_/id/82196/victor-wembanyama",
    "https://www.spotrac.com/nba/player/_/id/78116/jalen-duren",
]


def ask_for_url(default: str = "https://www.spotrac.com/nba/player/_/id/82196/victor-wembanyama") -> str:
    return input(f"Enter the player URL (default: {default}): ") or default

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
    url = ask_for_url()
    detail = scrape_player(url)
    #detail = select_columns(detail)
    print(detail.to_string())

    urls = PLAYERS_TO_SCRAPE
    details = scrape_players(urls)
    details = select_columns(details)
    print(details.to_string())


if __name__ == "__main__":
    main()
