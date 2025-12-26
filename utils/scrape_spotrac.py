import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Global constants
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
}

MAX_RETRIES = 3
RETRY_DELAY = 2
TIMEOUT = 10


def scrape_team_contracts(team, session):
    """
    Scrape contract data for a specific NBA team from Spotrac.
    """
    # Construct the URL for the team's contracts page
    url = f"https://www.spotrac.com/nba/{team}/yearly"

    # Retry logic for handling transient errors
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(url, headers=HEADERS, timeout=TIMEOUT)

            if response.status_code == 200:
                # Successful response
                break
            elif response.status_code == 502:
                # Bad Gateway, retry
                logging.warning(f"502 for {team} ({attempt}/{MAX_RETRIES})")
                time.sleep(RETRY_DELAY)
            else:
                # Other HTTP errors
                logging.error(f"{team}: HTTP {response.status_code}")
                return None

        except requests.RequestException as e:
            # Network-related errors, wait before retrying
            logging.warning(f"{team}: {e} ({attempt}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY)
    else:
        # All retries exhausted
        logging.error(f"{team}: failed after retries")
        return None

    soup = BeautifulSoup(response.content, "html.parser")

    # Function to extract data from a table
    def extract_table(table, season_headers):
        data = []
        for row in table.find("tbody").find_all("tr"):
            # Skip header or invalid rows
            cells = row.find_all("td")

            # Ensure there are enough cells
            if len(cells) < 2:
                continue

            # Extract player name and link
            player_tag = row.find("a")
            player_name = player_tag.text.strip() if player_tag else "Unknown"
            player_link = player_tag["href"] if player_tag else None

            # Extract position and age
            position = cells[1].text.strip()
            age = cells[2].text.strip()

            # Extract contract values for the seasons
            contract_values = []
            for col in cells[3:]:
                cell_text = col.get_text(strip=True)

                # Check for special contract types
                if "Two-Way" in cell_text:
                    contract_values.append("Two-Way")
                elif "UFA" in cell_text:
                    contract_values.append("UFA")
                elif "RFA" in cell_text:
                    contract_values.append("RFA")
                else:
                    # Extract dollar amounts
                    salary_matches = re.findall(r"\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?", cell_text)
                    contract_values.extend([s.replace(",", "") for s in salary_matches])

            # Limit to first 5 seasons
            contract_values = contract_values[:5]

            # Pad with None if fewer than expected seasons
            while len(contract_values) < len(season_headers):
                contract_values.append(None)

            # Append the extracted data
            data.append([player_name, player_link, position, age] + contract_values)

        return data

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
    all_data = []
    for table in tables:
        all_data.extend(extract_table(table, season_headers))

    columns = ["Player", "Player Link", "Position", "Age"] + season_headers
    return pd.DataFrame(all_data, columns=columns)

def scrape_all_teams():
    """
    Scrape contract data for all NBA teams from Spotrac.
    """
    teams = [
        "atlanta-hawks", "boston-celtics", "brooklyn-nets", "charlotte-hornets",
        "chicago-bulls", "cleveland-cavaliers", "dallas-mavericks", "denver-nuggets",
        "detroit-pistons", "golden-state-warriors", "houston-rockets", "indiana-pacers",
        "la-clippers", "los-angeles-lakers", "memphis-grizzlies", "miami-heat",
        "milwaukee-bucks", "minnesota-timberwolves", "new-orleans-pelicans",
        "new-york-knicks", "oklahoma-city-thunder", "orlando-magic", "philadelphia-76ers",
        "phoenix-suns", "portland-trail-blazers", "sacramento-kings", "san-antonio-spurs",
        "toronto-raptors", "utah-jazz", "washington-wizards",
    ]

    # Scrape all teams concurrently
    all_data = []

    # Use a session for connection pooling
    with requests.Session() as session:
        session.headers.update(HEADERS)

        # Use ThreadPoolExecutor for concurrent scraping
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {
                executor.submit(scrape_team_contracts, team, session): team
                for team in teams
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
                except Exception as e:
                    logging.error(f"{team} failed: {e}")

    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

def scrape_player_contracts(url):
    """
    Scrape contract details for a specific player from Spotrac.
    """
    try:
        # Make a request to the player's contract page
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        soup = BeautifulSoup(response.content, "html.parser")

        # Extract "Signed Using" details
        signed_using_selector = "#contracts > div > div > div.contract-wrapper.mb-5 > div.contract-details.row.m-0 > div:nth-child(5) > div.label"
        signed_using_element = soup.select_one(signed_using_selector)

        # Get the text of the next sibling element which contains the value
        signed_using_value = (
            signed_using_element.find_next_sibling().get_text().strip()
            if signed_using_element else None
        )

        # Extract "Drafted" details
        drafted_selector = "#main > section > article > div.row.m-0.mt-0.pb-3 > div.col-md-6 > div > div:nth-child(1) > span"
        drafted_element = soup.select_one(drafted_selector)

        drafted_value = (
            drafted_element.get_text().strip()
            if drafted_element else None
        )

        return signed_using_value, drafted_value

    except Exception as e:
        return None, None


if __name__ == "__main__":
    # Example usage: Scrape San Antonio Spurs contracts and print the resulting DataFrame
    team_df = scrape_team_contracts("san-antonio-spurs", requests.Session())
    print(team_df)

    # Example usage: Scrape contract details for Victor Wembanyama
    player_df = scrape_player_contracts("https://www.spotrac.com/nba/player/_/id/82196/victor-wembanyama")
    print(player_df)
