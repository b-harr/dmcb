import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from main import scrape_sportsws_stats, scrape_cache


if __name__ == "__main__":
    sportsws_cache_path = "dmcb-dev/tests/cache/sportsws.html"
    df = scrape_sportsws_stats(scrape_cache(sportsws_cache_path))
    print(df)