import os
import sys

import pandas as pd

# Dynamically add the project root to PYTHONPATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.get_contract_types import get_links_to_scrape


def test_get_links_to_scrape_rescrapes_rows_with_missing_values(tmp_path):
    output_csv = tmp_path / "contract_types.csv"

    existing_df = pd.DataFrame(
        [
            {
                "Player": "Existing Player",
                "Player Link": "link-a",
                "Player Key": "player-a",
                "Signed Using": "2024 / UFA",
                "Drafted": "2020",
            },
            {
                "Player": "Needs Re-scrape",
                "Player Link": "link-b",
                "Player Key": "player-b",
                "Signed Using": None,
                "Drafted": None,
            },
        ]
    )
    existing_df.to_csv(output_csv, index=False)

    to_scrape = get_links_to_scrape(["link-a", "link-b", "link-c"], str(output_csv))

    assert to_scrape == ["link-b", "link-c"]

    cleaned_df = pd.read_csv(output_csv)
    assert cleaned_df["Player Link"].tolist() == ["link-a"]
