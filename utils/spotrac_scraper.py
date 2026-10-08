import os
import sys
import logging
import time
import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

from utils.text_formatter import make_player_key

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

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
TEAMS = [
    "atlanta-hawks", "boston-celtics", "brooklyn-nets",
    "charlotte-hornets", "chicago-bulls", "cleveland-cavaliers",
    "dallas-mavericks", "denver-nuggets", "detroit-pistons",
    "golden-state-warriors", "houston-rockets", "indiana-pacers",
    "la-clippers", "los-angeles-lakers", "memphis-grizzlies",
    "miami-heat", "milwaukee-bucks", "minnesota-timberwolves",
    "new-orleans-pelicans", "new-york-knicks", "oklahoma-city-thunder",
    "orlando-magic", "philadelphia-76ers", "phoenix-suns",
    "portland-trail-blazers", "sacramento-kings", "san-antonio-spurs",
    "toronto-raptors", "utah-jazz", "washington-wizards",
]
PLAYER_DETAIL_COLUMNS = [
    "Player",
    "Link",
    "Key",
    "Drafted",
    "Signed Using",
    #"Team",
    #"Position",
    #"Age",
    #"Exp",
    #"Country",
    #"College",
    # Add more columns as needed
]

def scrape_team_url(url: str) -> pd.DataFrame | None:
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"Error fetching {url}: {e}")
        return None

    soup = BeautifulSoup(response.content, "html.parser")
    return soup

def extract_team_contracts(table: BeautifulSoup) -> list[list[str] | None]:
    data = []
    for row in table.select("tbody tr"):
        cells = row.find_all("td")

        player = cells[0].get("data-export").strip() if cells[0].get("data-export") else None
        link = cells[0].find("a")["href"] if cells[0].find("a") else None
        position = cells[1].get("data-export").strip() if cells[1].get("data-export") else None
        age = cells[2].get("data-export").strip() if cells[2].get("data-export") else None

        values = [
            get_contract_value(cell)
            for cell in cells[3:]
        ]
        # Limit to the first 5 seasons of contract values
        values = values[:5]

        data.append([player, link, position, age, *values])

    return data

def get_contract_value(cell: BeautifulSoup) -> str | None:
    export_value = cell.get("data-export").strip() if cell.get("data-export") else None
    pill = cell.select_one(".pill-start")
    pill_value = pill.get_text(strip=True) if pill else None

    for status in ("UFA", "RFA", "Two-Way"):
        if pill_value.startswith(status):
            return status

    if export_value == "0":
        return "$0"

    if pill_value.startswith("$"):
        return pill_value.replace(",", "")

    return export_value

def scrape_team(team: str) -> pd.DataFrame | None:
    url = f"https://www.spotrac.com/nba/{team}/yearly"

    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"Error fetching {url}: {e}")
        return None

    soup = BeautifulSoup(response.content, "html.parser")

    # Find both active and pending contract tables
    tables = []
    for table_id in ["dataTable-active", "dataTable-pending"]:
        table = soup.find("table", {"id": table_id})
        if table is not None:
            tables.append(table)

    if not tables:
        logging.warning(f"No contracts tables found for {team}")
        return None

    # Extract season headers from the first table
    headers = [th.text.strip() for th in tables[0].find_all("th")]
    season_headers = [h for h in headers if h.startswith("20")]
    season_headers = season_headers[:5]

    # Extract data from all found tables
    data = []
    for table in tables:
        data.extend(extract_team_contracts(table))

    columns = ["Player", "Player Link", "Position", "Age"] + season_headers

    return pd.DataFrame(data, columns=columns)

def scrape_team_with_retries(team: str) -> pd.DataFrame | None:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return scrape_team(team)
        except Exception as e:
            if attempt == MAX_RETRIES:
                raise
            logging.warning(f"{team} scrape failed ({attempt}/{MAX_RETRIES}), retrying: {e}")
            time.sleep(RETRY_DELAY)

def scrape_teams() -> pd.DataFrame:
    all_data = []
    failures = []

    # Use a session for connection pooling
    with requests.Session() as session:
        session.headers.update(HEADERS)

        # Use ThreadPoolExecutor for concurrent scraping
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {
                executor.submit(scrape_team_with_retries, team): team
                for team in TEAMS
            }

            # Collect results as they complete
            for future in as_completed(futures):
                team = futures[future]
                try:
                    df = future.result()
                    if df is not None:
                        df["Team"] = team
                        all_data.append(df)
                        logging.info(f"✔ Finished {team}")
                    else:
                        failures.append(f"{team}: no data returned")
                        logging.error(f"{team} returned no data")
                except Exception as e:
                    logging.error(f"{team} failed: {e}")
                    failures.append(f"{team}: {e}")

    if failures:
        raise RuntimeError("One or more teams failed to scrape: " + "; ".join(failures))

    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

def scrape_player_url(url: str) -> pd.DataFrame | None:
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"Error fetching {url}: {e}")
        return None

    soup = BeautifulSoup(response.content, "html.parser")
    return soup

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
    if soup is None:
        return pd.DataFrame()
    data = scrape_player_details(soup)
    data["Key"] = data["Player"].apply(make_player_key)

    return data[PLAYER_DETAIL_COLUMNS]


if __name__ == "__main__":
    team = scrape_team("detroit-pistons")
    print(team)

    player = scrape_player("https://www.spotrac.com/nba/player/_/id/82196")
    print(player)
