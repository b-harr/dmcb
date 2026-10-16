import os
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import pandas as pd
import requests

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

from scripts import pull_details, utils


class TestPullDetails(unittest.TestCase):
    def test_two_way_first_contract_value_is_not_scraped(self):
        contracts = pd.DataFrame(
            {
                "Player Link": ["two-way-url", "standard-url"],
                "2026-27": [" Two-Way ", "$1,000,000"],
            }
        )

        urls = pull_details.get_player_urls_to_scrape(
            contracts, pd.DataFrame(columns=["Player Link", "Signed Using"])
        )

        self.assertEqual(urls, ["standard-url"])

    def test_saved_csv_is_sorted_by_player_key(self):
        contract_types = pd.DataFrame(
            {
                "Player": ["Zed", "Abe"],
                "Player Link": ["zed-url", "abe-url"],
                "Player Key": ["zed", "abe"],
                "Signed Using": ["UFA", "RFA"],
                "Drafted": ["", ""],
            }
        )

        with tempfile.TemporaryDirectory() as directory:
            output_path = os.path.join(directory, "contract_types.csv")
            with patch.object(pull_details, "OUTPUT_PATH", output_path):
                pull_details._save_contract_types(contract_types)
            saved = pd.read_csv(output_path)

        self.assertEqual(saved["Player Key"].tolist(), ["abe", "zed"])

    def test_upsert_uses_player_link_index(self):
        source_players = pd.DataFrame(
            {
                "Player": ["Alondes Williams"],
                "Player Key": ["alondes-williams"],
            },
            index=pd.Index(
                ["https://www.spotrac.com/nba/player/_/id/78284/alondes-williams"],
                name="Player Link",
            ),
        )
        contract_types = pd.DataFrame(columns=pull_details.OUTPUT_COLUMNS)

        updated = pull_details._upsert_contract_details(
            contract_types,
            source_players.iloc[0],
            pd.Series({"Signed Using": "UFA", "Drafted": ""}),
        )

        self.assertEqual(updated.loc[0, "Player Link"], source_players.index[0])
        self.assertEqual(updated.loc[0, "Signed Using"], "UFA")

    def test_403_response_is_not_swallowed_by_page_fetch(self):
        response = Mock()
        response.raise_for_status.side_effect = requests.HTTPError(
            "403 Client Error: Forbidden for url", response=Mock(status_code=403)
        )

        with patch.object(utils.requests, "get", return_value=response):
            with self.assertRaises(requests.HTTPError):
                utils._save_page("https://example.com/player", "ignored.html")

    def test_403_stops_player_retries(self):
        error = RuntimeError("403 Client Error: Forbidden for url 'https://example.com'")
        with patch.object(pull_details, "scrape_players", side_effect=error) as scrape:
            with self.assertRaises(pull_details.ForbiddenScrapeError):
                pull_details._scrape_player_with_retries("https://example.com")

        scrape.assert_called_once_with(["https://example.com"])


if __name__ == "__main__":
    unittest.main()