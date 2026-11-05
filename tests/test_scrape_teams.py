import os
import sys

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

from dmcb.services.spotrac import scrape_teams

def main():
    nba_contracts = scrape_teams()
    print(nba_contracts)


if __name__ == "__main__":
    main()
