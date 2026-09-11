import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from main import scrape_team_contracts
from bs4 import BeautifulSoup


def main():
    input_path = "dmcb-dev/tests/cache/team.html"

    with open(input_path, "r", encoding="utf-8") as file:
        soup = BeautifulSoup(file, "html.parser")

    output_active_path = "dmcb-dev/tests/data/team_active.csv"
    output_pending_path = "dmcb-dev/tests/data/team_pending.csv"

    active_df = scrape_team_contracts(soup, table_id="dataTable-active")
    active_df.to_csv(output_active_path, mode="w", index=False, encoding="utf-8")

    pending_df = scrape_team_contracts(soup, table_id="dataTable-pending")
    pending_df.to_csv(output_pending_path, mode="w", index=False, encoding="utf-8")


if __name__ == "__main__":
    main()