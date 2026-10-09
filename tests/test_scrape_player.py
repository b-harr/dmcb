import os
import sys

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

from utils.spotrac_scraper import scrape_player


def get_url(url: str = "https://www.spotrac.com/nba/player/_/id/82196/victor-wembanyama") -> str:
    return input(f"Enter player url (default: {url}): ") or url

def main():
    url = get_url()
    df = scrape_player(url)
    print(df)


if __name__ == "__main__":
    main()
