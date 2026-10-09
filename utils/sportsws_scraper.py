import os
import sys
import logging
import requests
import pandas as pd
from lxml import html

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

from utils.text_formatter import make_player_key

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
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


def scrape_sportsws() -> pd.DataFrame:
    url = "https://sports.ws/nba/stats"
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
        logging.info(f"Successfully fetched data from {url}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching data from {url}: {e}")
        return pd.DataFrame()

    tree = html.fromstring(response.content)
    players = tree.xpath("//td[1]//a")

    # Extract data into a list of dictionaries then convert to a DataFrame
    player_data = []
    for player in players:
        name = player.text.strip() if player.text else ""
        link = "https://sports.ws" + player.get("href")
        tail = player.tail.strip() if player.tail else ""

        player_data.append({"Name": name, "Player Link": link, "Tail": tail})
    df = pd.DataFrame(player_data)

    # Split the Tail into Team and Position then drop Tail
    df[["Team", "Position"]] = df["Tail"].str.extract(r",\s*([\w*]+),\s*(\w+)")
    df = df.drop(columns=["Tail"])

    # Filter rows where Name is blank
    df = df[df["Name"].str.strip().ne(".")]  # Exclude blank/whitespace-only names
    df = df.dropna(subset=["Name"])  # Also drop rows where Name is NaN
    df = df.fillna("")

    return df

def process_data(df: pd.DataFrame) -> pd.DataFrame:
    df["Player Key"] = df["Player Link"].str.replace(
        "https://sports.ws/nba/", "", regex=False
    ).apply(make_player_key)
    column_order = ["Name", "Player Link", "Player Key", "Position"]
    return df[column_order].sort_values(by="Player Key").reset_index(drop=True)


if __name__ == "__main__":
    raw_data = scrape_sportsws()
    pos_data = process_data(raw_data)
    print(pos_data)
