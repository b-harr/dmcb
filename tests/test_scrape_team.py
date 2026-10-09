import os
import sys

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

from utils.spotrac_scraper import scrape_team, HEADERS, TIMEOUT

OUTPUT_DIR = os.path.join(".cache", "teams")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_team(team: str = "san-antonio-spurs") -> str:
    return input(f"Enter team name (default: {team}): ") or team

def main():
    team = get_team()
    team_contracts = scrape_team(team)
    print(team_contracts)


if __name__ == "__main__":
    main()
