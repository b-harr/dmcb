import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from main import scrape_player_details, scrape_cache, scrape_website


if __name__ == "__main__":
    player_path = os.path.join(project_root, "tests/cache/player.html")
    player_url = "https://www.spotrac.com/nba/player/_/id/82196/victor-wembanyama"

    soup = scrape_cache(player_path)
    #soup = scrape_website(player_url)

    df = scrape_player_details(soup)
    print(df)