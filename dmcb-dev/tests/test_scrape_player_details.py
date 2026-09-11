import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from main import scrape_player_details, scrape_cache, scrape_website


if __name__ == "__main__":
    import pandas as pd

    player_path = "dmcb-dev/tests/cache/player.html"
    player_url = "https://www.spotrac.com/nba/player/_/id/17852/tyus-jones"

    #soup = scrape_cache(player_path)
    soup = scrape_website(player_url)

    data = scrape_player_details(soup)
    df = pd.DataFrame(data).set_index(0).T
    print(df)