import os
import sys
from bs4 import BeautifulSoup
import csv

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from main import extract_multiyear_table


def main():
    input_path = "dmcb-dev/tests/cache/team.html"

    with open(input_path, "r", encoding="utf-8") as file:
        soup = BeautifulSoup(file, "html.parser")

    output_active_path = "dmcb-dev/tests/data/team_active.csv"
    output_pending_path = "dmcb-dev/tests/data/team_pending.csv"

    headers, active_table_data = extract_multiyear_table(soup, table_id="dataTable-active")
    with open(output_active_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(active_table_data)

    headers, pending_table_data = extract_multiyear_table(soup, table_id="dataTable-pending")
    with open(output_pending_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(pending_table_data)


if __name__ == "__main__":
    main()