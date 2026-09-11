import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from main import scrape_team_contracts, scrape_cache


def main():
    input_path = os.path.join(os.path.dirname(__file__), "cache/team.html")
    output_active_path = os.path.join(os.path.dirname(__file__), "data/team_active.csv")
    output_pending_path = os.path.join(os.path.dirname(__file__), "data/team_pending.csv")

    soup = scrape_cache(input_path)

    active_df = scrape_team_contracts(soup, table_id="dataTable-active")
    active_df.to_csv(output_active_path, mode="w", index=False, encoding="utf-8")

    pending_df = scrape_team_contracts(soup, table_id="dataTable-pending")
    pending_df.to_csv(output_pending_path, mode="w", index=False, encoding="utf-8")


if __name__ == "__main__":
    main()