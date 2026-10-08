import os
import sys
import requests
import re
import pandas as pd
from bs4 import BeautifulSoup

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

from utils.spotrac_scraper import scrape_player

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/26.6.2 Safari/605.1.15"
    )
}
TIMEOUT = 10
OUTPUT_DIR = os.path.join(".cache", "players")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_url(url: str = "https://www.spotrac.com/nba/player/_/id/82196/victor-wembanyama") -> str:
    return input(f"Enter player url (default: {url}): ") or url

def save_page(url: str) -> BeautifulSoup:
    filename = re.sub("https://www.spotrac.com/nba/player/_/id/", "", url)
    filename = re.sub("/", "-", filename) + ".html"
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    soup = BeautifulSoup(response.content, "html.parser")
    if response.status_code == 200:
        with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
            f.write(soup.prettify())
        print(f"Page saved to {filename}")
        return soup
    else:
        print(f"Failed to fetch page. Status code: {response.status_code}")
        return None

def main():
    url = get_url()
    df = scrape_player(url)
    print(df)


if __name__ == "__main__":
    main()
