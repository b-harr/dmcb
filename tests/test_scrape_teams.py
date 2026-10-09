import os
import sys

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

from utils.spotrac_scraper import scrape_teams

OUTPUT_DIR = os.path.join(".cache", "teams")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def main():
    nba_contracts = scrape_teams()
    print(nba_contracts.to_string(index=False))


if __name__ == "__main__":
    main()
