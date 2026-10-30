import os
import logging
import re
import requests
import unicodedata
import pandas as pd
from bs4 import BeautifulSoup
from nba_api.stats.endpoints import leaguedashplayerstats

from dmcb.services.google_sheets import GoogleSheetsManager

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/26.6.2 Safari/605.1.15"
    )
}
TIMEOUT = 10

PLAYER_KEY_OVERRIDES = {
    "cam-thomas": "cameron-thomas",
    "oliviermaxence-prosper": "olivier-maxence-prosper",
    "herbert-jones": "herb-jones",
    "tristan-dasilva": "tristan-da-silva",
    #"yang-hansen": "hansen-yang",
}

CAPITALIZED_WORDS = {
    "la", "rfa", "ufa", "mle", "na"
}
MINOR_WORDS = {
    "a", "an", "the", "and", "or",
    "in", "on", "of", "for", "to",
    "by", "with", "at", "vs",
}
HYPHENATED_WORDS = {
    "non", "mid", "bi", "re",
}

TEAMS = {
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
}


def make_player_key(name: str) -> str:
    # Remove accents and convert to lowercase
    name = unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode("utf-8")
    name = name.lower().strip()

    # Normalize spaces and special characters
    name = re.sub(r"\s+", "-", name)
    name = re.sub(r"[^\w-]", "", name)

    # Remove common suffixes
    key = re.sub(r"-(sr|jr|ii|iii|iv|v|vi|vii|viii|ix|x)$", "", name)

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

def scrape_team(
    team: str,
    session: requests.Session | None = None,
    season_limit: int | None = 5,
) -> pd.DataFrame:
    from dmcb.services.spotrac import scrape_team as implementation

    return implementation(team, session=session, season_limit=season_limit)

def scrape_teams() -> pd.DataFrame:
    from dmcb.services.spotrac import scrape_teams as implementation

    return implementation()

def scrape_player(
    url: str,
    detail_fields: list[str] | None = None,
) -> pd.DataFrame:
    from dmcb.services.spotrac import scrape_player as implementation

    return implementation(url, detail_fields=detail_fields)

def scrape_players(
    urls: list[str],
    detail_fields: list[str] | None = None,
) -> pd.DataFrame:
    from dmcb.services.spotrac import scrape_players as implementation

    return implementation(urls, detail_fields=detail_fields)

def scrape_positions() -> pd.DataFrame:
    df = _scrape_sportsws_stats()
    df = _process_sportsws_data(df)
    return df

def scrape_bbref_stats(year: int) -> pd.DataFrame:
    url = f"https://www.basketball-reference.com/leagues/NBA_{year}_totals.html"

    soup = _save_page(url, f".cache/stats/bbref-{year}.html")
    if soup is None:
        raise RuntimeError(f"Could not fetch Basketball-Reference stats for {year}.")
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

def scrape_nba_stats(year: int) -> pd.DataFrame:
    season_str = f"{year-1}-{str(year)[-2:]}"  # e.g., 2027 => 2026-27

    stats = leaguedashplayerstats.LeagueDashPlayerStats(season=season_str)
    df = stats.get_data_frames()[0]

    df = df.dropna(subset=["PLAYER_NAME"])

    df.rename(columns={
        "PLAYER_NAME": "Player",
        "TEAM_ABBREVIATION": "Team",
        "GP": "G",
        "MIN": "MP",
        "PTS": "PTS",
        "REB": "TRB",
        "AST": "AST",
        "STL": "STL",
        "BLK": "BLK",
        "TO": "TOV",
        "PF": "PF"
    }, inplace=True)

    column_order = ["Player", "Team", "G", "MP", "PTS", "TRB", "AST", "STL", "BLK", "TOV", "PF"]
    df = df[column_order]

    return df

def scrape_owners(sheet: str, output: str) -> pd.DataFrame:
    try:
        sheets_manager = GoogleSheetsManager()
        raw_data = sheets_manager.read_data(sheet)
    except Exception as e:
        raise RuntimeError(
            f"Could not read owner data from Google Sheets worksheet '{sheet}'."
        ) from e

    if not raw_data:
        return pd.DataFrame(columns=["Owner", "Player", "Player Key"])

    header = raw_data[0]
    rows = raw_data[1:] if len(raw_data) > 1 else []

    if len(header) < 4:
        raise ValueError(
            f"Google Sheets worksheet '{sheet}' must include Owner in column A "
            "and Player in column D."
        )

    df = pd.DataFrame(rows, columns=[str(col).strip() for col in header])
    df = df.iloc[:, [0, 3]].copy()
    df.columns = ["Owner", "Player"]

    df["Player Key"] = df["Player"].apply(make_player_key)
    df = df.dropna(subset=["Player Key"])
    df = df[df["Player Key"] != ""]

    try:
        df.to_csv(output, index=False)
    except OSError as e:
        raise OSError(f"Could not save owner data to '{output}': {e}") from e
    logging.info(f"Data saved to {output}")

    return df

def merge_owners(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        logging.info("DataFrame is empty, returning as is.")
        return df

    owners_path = os.path.join("data", "dmcb_owners.csv")
    owners = pd.read_csv(owners_path)

    if owners.empty:
        logging.info("Owners DataFrame is empty, returning as is.")
        return df

    merged_df = df.copy()
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

def save_owned(df: pd.DataFrame, output: str) -> pd.DataFrame:
    if "Owner" not in df.columns:
        raise ValueError("DataFrame must contain an Owner column.")

    owned_df = df[df["Owner"].fillna("").astype(str).str.strip().ne("")].copy()
    owned_df.to_csv(output, index=False)
    logging.info(f"Saved {len(owned_df)} owned contracts to {output}.")
    return owned_df

def _save_page(url: str, output: str, session: requests.Session | None = None) -> BeautifulSoup | None:
    try:
        if session is None:
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        else:
            response = session.get(url, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"Error fetching {url}: {e}")
        if isinstance(e, requests.HTTPError) and getattr(e.response, "status_code", None) == 403:
            raise
        return None
    soup = BeautifulSoup(response.content, "html.parser")
    os.makedirs(os.path.dirname(output), exist_ok=True)
    with open(output, "w", encoding="utf-8") as file:
        file.write(soup.prettify())
    return soup

def _extract_team_contracts(
    table: BeautifulSoup,
    season_limit: int | None = 5,
) -> list[list[str] | None]:
    from dmcb.services.spotrac import _extract_team_contracts as implementation

    return implementation(table, season_limit=season_limit)

def _scrape_team_with_retries(
    team: str,
    season_limit: int | None = 5,
) -> pd.DataFrame | None:
    from dmcb.services.spotrac import _scrape_team_with_retries as implementation

    return implementation(team, season_limit=season_limit)

def _extract_player_details(soup: BeautifulSoup) -> pd.DataFrame:
    from dmcb.services.spotrac import _extract_player_details as implementation

    return implementation(soup)

def _scrape_sportsws_stats() -> pd.DataFrame:
    url = "https://sports.ws/nba/stats"
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
        logging.info(f"Successfully fetched data from {url}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching data from {url}: {e}")
        raise RuntimeError(f"Could not fetch Sports.ws positions from {url}: {e}") from e

    soup = BeautifulSoup(response.content, "html.parser")
    players = soup.select("td:first-child a")

    # Extract data into a list of dictionaries then convert to a DataFrame
    player_data = []
    for player in players:
        name = player.get_text(strip=True)
        link = "https://sports.ws" + player.get("href")
        sibling = player.next_sibling
        tail = sibling.strip() if isinstance(sibling, str) else ""

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
    df = df[~df["Player Key"].str.contains("placeholder", case=False, na=False)].copy()
    return df[column_order].sort_values(by="Player Key").reset_index(drop=True)
