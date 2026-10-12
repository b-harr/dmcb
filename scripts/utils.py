import os
import sys
import logging
import gspread
import json
import re
import requests
import time
import unicodedata
import pandas as pd
from bs4 import BeautifulSoup
from lxml import html
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from urllib.parse import urlparse

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

load_dotenv()

GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
GOOGLE_SHEETS_URL = os.getenv("GOOGLE_SHEETS_URL")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/26.6.2 Safari/605.1.15"
    )
}
TIMEOUT = 10
RETRY_DELAY = 5
MAX_RETRIES = 3

PLAYER_KEY_OVERRIDES = {
    "cam-thomas": "cameron-thomas",
    "oliviermaxence-prosper": "olivier-maxence-prosper",
    "herbert-jones": "herb-jones",
    "tristan-dasilva": "tristan-da-silva",
    #"yang-hansen": "hansen-yang",
}

CAPITALIZED_WORDS = {
    "la", "rfa", "ufa", "mle",
}
MINOR_WORDS = {
    "a", "an", "the", "and", "or",
    "in", "on", "of", "for", "to",
    "by", "with", "at", "vs",
}
HYPHENATED_WORDS = {
    "non", "mid", "bi", "re",
}

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


def make_player_key(name: str) -> str:
    # Remove accents and convert to lowercase
    name = unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode("utf-8")
    name = name.lower().strip()

    # Normalize spaces and special characters
    name = re.sub(r"\s+", "-", name)
    name = re.sub(r"[^\w-]", "", name)

    # Remove common suffixes
    key = re.sub(r"-(sr|jr|ii|iii|iv|v|vi|vii)$", "", name)

    # Apply overrides if the cleaned name matches any known exceptions
    if key in PLAYER_KEY_OVERRIDES:
        return PLAYER_KEY_OVERRIDES[key]

    return key

def make_title_case(text: str) -> str:
    # Split the text into words by spaces or hyphens
    words = re.split(r"[-\s]", text)
    formatted_words = []
    i = 0

    # Iterate through each word and apply title case rules
    while i < len(words):
        word = words[i].lower()

        # Handle common abbreviations
        if word in CAPITALIZED_WORDS:
            formatted_words.append(word.upper())

        # Handle exception words with hyphenation
        elif word in HYPHENATED_WORDS and i < len(words) - 1:
            formatted_words.append(f"{word.capitalize()}-{words[i + 1].capitalize()}")
            # Skip the next word as it's already processed
            i += 1

        # Handle minor words
        elif word in MINOR_WORDS:
            formatted_words.append(word if i != 0 and i != len(words) - 1 else word.capitalize())

        # Capitalize alphabetic words; retain numbers
        else:
            formatted_words.append(word.capitalize() if word.isalpha() else word)

        # Move to the next word
        i += 1

    # Join the formatted words with spaces
    title_text = " ".join(formatted_words)
    # Special case: Replace "Sign and Trade" with "Sign-and-Trade"
    title_text = re.sub("Sign and Trade", "Sign-and-Trade", title_text)

    return title_text

def _save_page(url: str, output: str) -> BeautifulSoup:
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"Error fetching {url}: {e}")
        return None
    soup = BeautifulSoup(response.content, "html.parser")
    with open(output, "w", encoding="utf-8") as file:
        file.write(soup.prettify())
    return soup

def _extract_team_contracts(table: BeautifulSoup) -> list[list[str] | None]:
    data = []
    for row in table.select("tbody tr"):
        cells = row.find_all("td")

        player = cells[0].get("data-export").strip() if cells[0].get("data-export") else None
        link = cells[0].find("a")["href"] if cells[0].find("a") else None
        position = cells[1].get("data-export").strip() if cells[1].get("data-export") else None
        age = cells[2].get("data-export").strip() if cells[2].get("data-export") else None

        def _get_contract_value(cell: BeautifulSoup) -> str | None:
            export_value = cell.get("data-export").strip() if cell.get("data-export") else None
            pill = cell.select_one(".pill-start")
            pill_value = pill.get_text(strip=True) if pill else None

            for status in ("UFA", "RFA", "Two-Way", "Exhibit 10", "Exhibit 9"):
                if pill_value.startswith(status):
                    return status

            if export_value == "0":
                return "$0"

            if pill_value.startswith("$"):
                return pill_value.replace(",", "")

            return export_value

        values = [
            _get_contract_value(cell)
            for cell in cells[3:]
        ]
        # Limit to the first 5 seasons of contract values
        values = values[:5]

        data.append([player, link, position, age, *values])

    return data

def scrape_team(team: str) -> pd.DataFrame:
    url = f"https://www.spotrac.com/nba/{team}/yearly"

    soup = _save_page(url, f".cache/teams/{team}.html")
    if soup is None:
        return pd.DataFrame()

    # Find both active and pending contract tables
    tables = []
    for table_id in ["dataTable-active", "dataTable-pending"]:
        table = soup.find("table", {"id": table_id})
        if table is not None:
            tables.append(table)

    if not tables:
        logging.warning(f"No contracts tables found for {team}")
        return pd.DataFrame()

    # Extract season headers from the first table
    headers = [th.text.strip() for th in tables[0].find_all("th")]
    season_headers = [h for h in headers if h.startswith("20")]
    season_headers = season_headers[:5]

    # Extract data from all found tables
    data = []
    for table in tables:
        data.extend(_extract_team_contracts(table))

    columns = ["Player", "Player Link", "Position", "Age"] + season_headers

    return pd.DataFrame(data, columns=columns)

def _scrape_team_with_retries(team: str) -> pd.DataFrame | None:
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
                executor.submit(_scrape_team_with_retries, team): team
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

def _extract_player_details(soup: BeautifulSoup) -> pd.DataFrame:
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
    player = "-".join(urlparse(url).path.rstrip("/").split("/")[-2:])

    soup = _save_page(url, f".cache/players/{player}.html")
    if soup is None:
        return pd.DataFrame()
    data = _extract_player_details(soup)
    data["Key"] = data["Player"].apply(make_player_key)
    columns = ["Player", "Player Link", "Player Key", "Signed Using", "Drafted"]
    return data[columns]

def scrape_players(urls: list[str]) -> pd.DataFrame:
    all_data = []
    failures = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(scrape_player, url): url for url in urls}
        for future in as_completed(futures):
            url = futures[future]
            try:
                df = future.result()
                if not df.empty:
                    all_data.append(df)
                    logging.info(f"✔ Finished {url}")
                else:
                    failures.append(f"{url}: no data returned")
                    logging.error(f"{url} returned no data")
            except Exception as e:
                logging.error(f"{url} failed: {e}")
                failures.append(f"{url}: {e}")

    if failures:
        raise RuntimeError("One or more players failed to scrape: " + "; ".join(failures))

    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

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

def _process_sportsws_data(df: pd.DataFrame) -> pd.DataFrame:
    df["Player Key"] = df["Player Link"].str.replace(
        "https://sports.ws/nba/", "", regex=False
    ).apply(make_player_key)
    column_order = ["Name", "Player Link", "Player Key", "Position"]
    return df[column_order].sort_values(by="Player Key").reset_index(drop=True)

def scrape_bbref(year: int) -> pd.DataFrame:
    url = f"https://www.basketball-reference.com/leagues/NBA_{year}_totals.html"

    soup = _save_page(url, f".cache/stats/bbref_{year}.html")
    table = soup.find("table", {"id": "totals_stats"})
    if not table:
        raise ValueError("Table not found. Ensure the page structure has not changed.")

    headers = [th.get_text() for th in table.find("thead").find_all("th")][1:]
    headers.extend(["Player Link", "Team Link"])
    rows = table.find("tbody").find_all("tr")

    data = []
    for row in rows:
        if row.find("td"):
            row_data = [td.get_text() for td in row.find_all("td")]
            links = row.find_all("a")
            player_link, team_link = None, None

            for link in links:
                href = link.get("href", "")
                if "/players/" in href:
                    player_link = "https://www.basketball-reference.com" + href
                elif "/teams/" in href:
                    team_link = "https://www.basketball-reference.com" + href

            row_data.append(player_link)
            row_data.append(team_link)
            data.append(row_data)

    return pd.DataFrame(data, columns=headers)

class GoogleSheetsManager:
    def __init__(self):
        try:
            logging.info("Initializing GoogleSheetsManager...")
            self.gc = gspread.service_account(filename=GOOGLE_SHEETS_CREDENTIALS)
            self.sheet = self.gc.open_by_url(GOOGLE_SHEETS_URL)

            with open(GOOGLE_SHEETS_CREDENTIALS, "r") as file:
                credentials = json.load(file)
                self.service_account_email = credentials.get("client_email")
                
            logging.info(f"Successfully connected to Google Sheets. Service Account Email: {self.service_account_email}")
        except Exception as e:
            logging.error(f"Failed to initialize GoogleSheetsManager: {e}")
            raise

    def get_worksheet(self, sheet: str):
        try:
            worksheet = self.sheet.worksheet(sheet)
            logging.info(f"Accessed worksheet: {sheet}")
            return worksheet
        except Exception as e:
            logging.error(f"Error accessing worksheet '{sheet}': {e}")
            raise

    def read_data(self, sheet: str):
        try:
            worksheet = self.get_worksheet(sheet)
            data = worksheet.get_all_values()
            logging.info(f"Read {len(data)} rows from worksheet '{sheet}'.")
            return data
        except Exception as e:
            logging.error(f"Error reading data from worksheet '{sheet}': {e}")
            raise

    def write_data(self, data: pd.DataFrame, sheet: str, cell: str):
        try:
            worksheet = self.get_worksheet(sheet)
            worksheet.update(cell, data)
            logging.info(f"Written data to worksheet '{sheet}' starting at '{cell}'.")
        except Exception as e:
            logging.error(f"Error writing data to worksheet '{sheet}': {e}")
            raise

    def clear_data(self, sheet: str):
        try:
            worksheet = self.get_worksheet(sheet)
            worksheet.clear()
            logging.info(f"Cleared data from worksheet '{sheet}'.")
        except Exception as e:
            logging.error(f"Error clearing data in worksheet '{sheet}': {e}")
            raise

    def clear_range(self, sheet: str, range: str):
        try:
            worksheet = self.get_worksheet(sheet)
            worksheet.batch_clear([range])
            logging.info(f"Cleared range '{range}' in worksheet '{sheet}'.")
        except Exception as e:
            logging.error(f"Error clearing range '{range}' in worksheet '{sheet}': {e}")
            raise
