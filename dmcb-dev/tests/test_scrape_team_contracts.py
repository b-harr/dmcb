import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from main import scrape_website, scrape_cache, scrape_team_contracts


def test_web(team_url):
    contracts_web = scrape_website(team_url)
    df_web = scrape_team_contracts(contracts_web)
    return df_web

def test_cache(team_path):
    contracts_cache = scrape_cache(team_path)
    df_cache = scrape_team_contracts(contracts_cache)
    return df_cache


if __name__ == "__main__":
    #team_url = "https://www.spotrac.com/nba/toronto-raptors/yearly"
    #df_web = test_web(team_url)
    #print(df_web)

    team_cache = "dmcb-dev/tests/cache/team.html"
    df_cache = test_cache(team_cache)
    print(df_cache)