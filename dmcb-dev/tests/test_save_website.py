import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from main import save_website


if __name__ == "__main__":
    team_url = "https://www.spotrac.com/nba/la-clippers/yearly"
    output_path = os.path.join(project_root, "tests/cache/team.html")
    save_website(team_url, output_path)

    player_url = "https://www.spotrac.com/nba/player/_/id/82196/victor-wembanyama"
    output_path = os.path.join(project_root, "tests/cache/player.html")
    save_website(player_url, output_path)

    sportsws_url = "https://sports.ws/nba/stats"
    output_path = os.path.join(project_root, "tests/cache/sportsws.html")
    save_website(sportsws_url, output_path)

    bbref_url = "https://www.basketball-reference.com/leagues/NBA_2026_totals.html"
    output_path = os.path.join(project_root, "tests/cache/bbref.html")
    save_website(bbref_url, output_path)