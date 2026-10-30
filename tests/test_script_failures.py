import os
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

from scripts import (  # noqa: E402
    pull_contracts,
    pull_positions,
    pull_stats,
    pull_types,
    push_contracts,
    push_positions,
    push_stats,
    push_types,
)


PUSH_LOADERS = (
    (push_contracts.load_contracts, "contracts.csv"),
    (push_positions.load_positions, "positions.csv"),
    (push_stats.load_stats, "stats.csv"),
    (push_types.load_contract_types, "types.csv"),
)

PUSH_UPDATERS = (
    (push_contracts, "update_sheets", "clear_range", True),
    (push_positions, "update_sheets", "clear_data", False),
    (push_stats, "update_sheets", "clear_data", False),
    (push_types, "update_sheets", "clear_range", False),
)


class TestPushFailures(unittest.TestCase):
    def test_loaders_raise_for_missing_and_unreadable_files(self):
        for loader, filename in PUSH_LOADERS:
            with self.subTest(loader=loader.__name__, error="missing"):
                with tempfile.TemporaryDirectory() as directory:
                    missing_path = os.path.join(directory, filename)
                    with self.assertRaises(FileNotFoundError):
                        loader(missing_path)

            with self.subTest(loader=loader.__name__, error="unreadable"):
                with tempfile.TemporaryDirectory() as directory:
                    empty_path = os.path.join(directory, filename)
                    with open(empty_path, "w", encoding="utf-8"):
                        pass
                    with self.assertRaises(RuntimeError):
                        loader(empty_path)

    def test_empty_data_is_rejected_before_sheets_are_touched(self):
        for module, updater_name, _, has_range in PUSH_UPDATERS:
            with self.subTest(updater=module.__name__):
                updater = getattr(module, updater_name)
                arguments = ("Contracts", "A1:L751") if has_range else ("Contracts",)
                with patch.object(module, "GoogleSheetsManager") as manager:
                    with self.assertRaises(ValueError):
                        updater(pd.DataFrame(), *arguments)
                    with self.assertRaises(ValueError):
                        updater(pd.DataFrame({"Player": [" "]}), *arguments)
                manager.assert_not_called()

    def test_sheets_write_failures_are_raised(self):
        frame = pd.DataFrame({"Player": ["Player One"]})
        for module, updater_name, clear_name, has_range in PUSH_UPDATERS:
            with self.subTest(updater=module.__name__):
                updater = getattr(module, updater_name)
                arguments = ("Contracts", "A1:L751") if has_range else ("Contracts",)
                with patch.object(module, "GoogleSheetsManager") as manager_factory:
                    manager = manager_factory.return_value
                    manager.write_data.side_effect = OSError("Sheets unavailable")
                    with self.assertRaisesRegex(RuntimeError, "Failed to update"):
                        updater(frame, *arguments)
                    getattr(manager, clear_name).assert_called_once()


class TestPullFailures(unittest.TestCase):
    def test_contract_scrape_failures_are_raised(self):
        with patch.object(pull_contracts, "scrape_teams", side_effect=OSError("offline")):
            with self.assertRaisesRegex(RuntimeError, "Failed to scrape contracts"):
                pull_contracts.scrape_all()

        with patch.object(pull_contracts, "scrape_teams", return_value=pd.DataFrame()):
            with self.assertRaisesRegex(RuntimeError, "Failed to scrape contracts"):
                pull_contracts.scrape_all()

    def test_contract_owner_read_failure_is_raised(self):
        with patch.object(pull_contracts, "GoogleSheetsManager") as manager_factory:
            manager_factory.return_value.read_data.side_effect = OSError("Sheets unavailable")
            with self.assertRaisesRegex(RuntimeError, "Could not read owner data"):
                pull_contracts.get_owners()

    def test_contract_processing_and_save_reject_failures(self):
        with self.assertRaises(ValueError):
            pull_contracts.process_data(pd.DataFrame())
        with self.assertRaises(ValueError):
            pull_contracts.save_data(pd.DataFrame(), "contracts.csv")

        frame = pd.DataFrame({"Player": ["Player One"]})
        with patch.object(frame, "to_csv", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(RuntimeError, "Failed to save contracts"):
                pull_contracts.save_data(frame, "contracts.csv")

    def test_position_save_failures_are_raised(self):
        with self.assertRaises(ValueError):
            pull_positions.save_positions_data(pd.DataFrame(), "positions.csv")

        frame = pd.DataFrame({"Player": ["Player One"]})
        with patch.object(frame, "to_csv", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(RuntimeError, "Failed to save positions"):
                pull_positions.save_positions_data(frame, "positions.csv")

    def test_stats_save_failures_are_raised(self):
        columns = ["Player", "Team", *pull_stats.NUMERIC_COLUMNS]
        frame = pd.DataFrame([["Player One", "Team One", *([1] * 9)]], columns=columns)
        with (
            patch.object(pull_stats, "scrape_bbref_stats", return_value=frame),
            patch.object(pd.DataFrame, "to_csv", side_effect=OSError("disk full")),
        ):
            with self.assertRaisesRegex(RuntimeError, "Failed to save stats"):
                pull_stats.get_fantasy_stats(2027)

    def test_contract_type_scrape_failures_are_raised(self):
        with tempfile.TemporaryDirectory() as directory:
            input_path = os.path.join(directory, "contracts.csv")
            output_path = os.path.join(directory, "types.csv")
            pd.DataFrame(
                {
                    "Player": ["Player One"],
                    "Player Link": ["https://example.com/player-one"],
                    "Player Key": ["player-one"],
                }
            ).to_csv(input_path, index=False)

            with (
                patch.object(pull_types, "INPUT_PATH", input_path),
                patch.object(pull_types, "OUTPUT_PATH", output_path),
                patch.object(
                    pull_types,
                    "_scrape_player_with_retries",
                    side_effect=RuntimeError("scrape failed"),
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "Unfinished player scrapes"):
                    pull_types.main()


if __name__ == "__main__":
    unittest.main()
