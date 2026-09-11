import requests
from bs4 import BeautifulSoup
import pandas as pd
import unicodedata
import re


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
PLAYER_KEY_OVERRIDES = {
    "cam-thomas": "cameron-thomas",
    "oliviermaxence-prosper": "olivier-maxence-prosper",
    "herbert-jones": "herb-jones",
    "tristan-dasilva": "tristan-da-silva",
    #"yang-hansen": "hansen-yang",
    # add more as needed
}
TEAMS = [
    "atlanta-hawks", "boston-celtics", "brooklyn-nets", "charlotte-hornets",
    "chicago-bulls", "cleveland-cavaliers", "dallas-mavericks", "denver-nuggets",
    "detroit-pistons", "golden-state-warriors", "houston-rockets", "indiana-pacers",
    "la-clippers", "los-angeles-lakers", "memphis-grizzlies", "miami-heat",
    "milwaukee-bucks", "minnesota-timberwolves", "new-orleans-pelicans",
    "new-york-knicks", "oklahoma-city-thunder", "orlando-magic", "philadelphia-76ers",
    "phoenix-suns", "portland-trail-blazers", "sacramento-kings", "san-antonio-spurs",
    "toronto-raptors", "utah-jazz", "washington-wizards",
]


def make_player_key(name):
    # Remove accents
    normalized_name = unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode("utf-8")
    # Convert to lowercase and trim spaces
    cleaned_name = normalized_name.lower().strip()
    # Replace spaces with hyphens
    cleaned_name = re.sub(r"\s+", "-", cleaned_name)
    # Remove non-alphanumeric characters
    cleaned_name = re.sub(r"[^\w-]", "", cleaned_name)
    # Remove common suffixes
    player_key = re.sub(r"-(sr|jr|ii|iii|iv|v|vi|vii)$", "", cleaned_name)

    # Apply overrides if the cleaned name matches any known exceptions
    if player_key in PLAYER_KEY_OVERRIDES:
        return PLAYER_KEY_OVERRIDES[player_key]

    return player_key

def make_title_case(text):
    # List of minor words that should not be capitalized unless they are at the beginning or end
    minor_words = {"and", "or", "the", "in", "at", "for", "to", "by", "with", "a", "an", "of", "on", "vs"}
    hyphenated_words = {"non", "mid", "bi"}

    if text is None:
        return None

    # Split the text into words by spaces or hyphens
    words = re.split(r"[-\s]", text)
    formatted_words = []
    i = 0

    while i < len(words):
        word = words[i].lower()

        # Handle 'LA' specifically
        if word == "la":
            formatted_words.append("LA")
        elif word == "rfa":
            formatted_words.append("RFA")
        elif word == "ufa":
            formatted_words.append("UFA")
        elif word == "mle":
            formatted_words.append("MLE")
        # Handle exception words with hyphenation
        elif word in hyphenated_words and i < len(words) - 1:
            formatted_words.append(f"{word.capitalize()}-{words[i + 1].capitalize()}")
            i += 1  # Skip the next word as it's already processed
        # Handle minor words
        elif word in minor_words:
            formatted_words.append(word if i != 0 and i != len(words) - 1 else word.capitalize())
        # Capitalize alphabetic words; retain numbers
        else:
            formatted_words.append(word.capitalize() if word.isalpha() else word)

        i += 1

    # Join the formatted words with spaces
    formatted_words = " ".join(formatted_words)

    # Special case: Replace "Sign and Trade" with "Sign-and-Trade"
    formatted_words = re.sub("Sign and Trade", "Sign-and-Trade", formatted_words)

    return formatted_words

def scrape_website(url):
    page = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    soup = BeautifulSoup(page.content, "html.parser")
    return soup

def scrape_cache(path):
    with open(path, "r", encoding="utf-8") as file:
        content = file.read()
    soup = BeautifulSoup(content, "html.parser")
    return soup

def save_website(url, output_path):
    soup = scrape_website(url)
    with open(output_path, "w", encoding="utf-8") as file:
        file.write(soup.prettify())
    return soup

def scrape_team_contracts(soup, table_id="dataTable-active"):
    table = soup.find("table", id=table_id)
    if table is None:
        return pd.DataFrame()

    headers = [
        th.get_text(strip=True)
        for th in table.select("thead th")
    ]

    headers[0] = "Player"
    headers.insert(1, "Link")

    data = []
    for row in table.select("tbody tr"):
        cells = row.find_all("td")

        player = cells[0].get("data-export", "").strip()
        link = cells[0].find("a")["href"]
        position = cells[1].get("data-export", "").strip()
        age = cells[2].get("data-export", "").strip()

        def get_contract_value(cell):
            export_value = cell.get("data-export", "").strip()
            pill = cell.select_one(".pill-start")
            pill_text = pill.get_text(" ", strip=True) if pill else ""

            for status in ("UFA", "RFA", "Two-Way"):
                if pill_text.startswith(status):
                    return status

            if pill_text.startswith("$"):
                return pill_text.replace(",", "")

            return export_value

        values = [
            get_contract_value(cell)
            for cell in cells[3:]
        ]

        data.append([player, link, position, age, *values])

    df = pd.DataFrame(data, columns=headers)
    return df

def scrape_player_details(player_soup):
    table = player_soup.find("div", class_="contract-details")

    details = []
    for label, value in zip(
        table.find_all("div", class_="label"),
        table.find_all("div", class_="value"),
    ):
        details.append((
            label.get_text(strip=True),
            value.get_text(strip=True),
        ))

    df = pd.DataFrame(details).set_index(0).T
    return df

def scrape_sportsws_stats(sportsws_page):
    soup = scrape_website(sportsws_page)
    table = soup.find("table")
    rows = table.find("tbody").find_all("tr")
    data = []
    for row in rows:
        player = row.find_all("td")[0].text.strip()
        data.append(player)
    return data


if __name__ == "__main__":
    team_url = "https://www.spotrac.com/nba/san-antonio-spurs/yearly"
    team_contract = scrape_team_contracts(team_url)
    print(team_contract)

    player_url = "https://www.spotrac.com/nba/player/_/id/82196/victor-wembanyama"
    player_details = scrape_player_details(player_url)
    print(player_details)

    sportsws_url = "https://sports.ws/nba/stats"
    sportsws_stats = scrape_sportsws_stats(sportsws_url)
    print(sportsws_stats)