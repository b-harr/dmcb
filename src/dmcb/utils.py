import os
import logging
import re
import requests
import unicodedata
from bs4 import BeautifulSoup

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
