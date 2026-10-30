import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import requests
from bs4 import BeautifulSoup

from dmcb.models.records import PLAYER_DETAIL_COLUMNS
from dmcb.services import reconciliation, sheets, spotrac, sportsws
from dmcb.services.google_sheets import GoogleSheetsManager
from dmcb.utils import scrape_owners


class TestUtilityConfiguration(unittest.TestCase):
    def test_scrape_owners_raises_when_sheets_read_fails(self):
        error = RuntimeError("authentication failed")
        with (
            patch("dmcb.utils.GoogleSheetsManager") as manager_class,
            self.assertRaisesRegex(RuntimeError, "worksheet 'Owned'") as raised,
        ):
            manager_class.return_value.read_data.side_effect = error
            scrape_owners("Owned", "owners.csv")

        self.assertIs(raised.exception.__cause__, error)

    def test_scrape_owners_returns_schema_for_empty_worksheet(self):
        with patch("dmcb.utils.GoogleSheetsManager") as manager_class:
            manager_class.return_value.read_data.return_value = []
            owners = scrape_owners("Owned", "owners.csv")

        self.assertEqual(owners.columns.tolist(), ["Owner", "Player", "Player Key"])
        self.assertTrue(owners.empty)

    def test_scrape_owners_rejects_sheet_without_owner_and_player_columns(self):
        with (
            patch("dmcb.utils.GoogleSheetsManager") as manager_class,
            self.assertRaisesRegex(ValueError, "Owner in column A.*Player in column D"),
        ):
            manager_class.return_value.read_data.return_value = [["Owner", "Player"]]
            scrape_owners("Owned", "owners.csv")

    def test_sheets_manager_reads_environment_when_initialized(self):
        with tempfile.TemporaryDirectory() as directory:
            credentials_path = Path(directory) / "credentials.json"
            credentials_path.write_text(
                json.dumps({"client_email": "service@example.test"}),
                encoding="utf-8",
            )
            client = Mock()
            spreadsheet = Mock()
            client.open_by_url.return_value = spreadsheet
            with (
                patch.dict(
                    "os.environ",
                    {
                        "GOOGLE_SHEETS_CREDENTIALS": str(credentials_path),
                        "GOOGLE_SHEETS_URL": "https://example.test/sheet",
                    },
                ),
                patch("dmcb.services.google_sheets.load_dotenv") as load_dotenv,
                patch(
                    "dmcb.services.google_sheets.gspread.service_account",
                    return_value=client,
                ) as service_account,
            ):
                manager = GoogleSheetsManager()

        load_dotenv.assert_called_once_with()
        service_account.assert_called_once_with(filename=str(credentials_path))
        client.open_by_url.assert_called_once_with("https://example.test/sheet")
        self.assertIs(manager.sheet, spreadsheet)
        self.assertEqual(manager.service_account_email, "service@example.test")


class TestSpotracServices(unittest.TestCase):
    def test_legacy_scrape_team_import_delegates_to_spotrac_service(self):
        frame = pd.DataFrame([{"Player": "Test Player"}])
        with patch.object(spotrac, "scrape_team", return_value=frame) as scrape:
            result = spotrac.utils.scrape_team("boston-celtics", season_limit=None)

        self.assertIs(result, frame)
        scrape.assert_called_once_with(
            "boston-celtics", session=None, season_limit=None
        )

    def test_team_contract_parser_handles_missing_pills_and_all_season_values(self):
        table = BeautifulSoup(
            """
            <table><tbody><tr>
              <td data-export="Test Player">
                <a href="/nba/player/_/id/1/test-player">Test Player</a>
                <div class="text-muted">(G, 25)</div>
              </td>
              <td><span class="pill-start">$1,000,000</span></td>
              <td data-export="0"></td>
              <td></td>
            </tr></tbody></table>
            """,
            "html.parser",
        ).table
        parsed = spotrac._extract_team_contracts(table, season_limit=None)
        self.assertEqual(parsed[0][4:], ["$1000000", "$0", None])

    def test_contract_scrape_preserves_all_years_and_displays_latest_five(self):
        source = pd.DataFrame(
            {
                "Player": ["Test Player"],
                "Player Link": ["https://example.test/player"],
                "Position": ["G"],
                "Age": ["25"],
                "2022-23": ["$1"],
                "2023-24": ["$2"],
                "2024-25": ["$3"],
                "2025-26": ["$4"],
                "2026-27": ["$5"],
                "2027-28": ["$6"],
            }
        )

        with patch.object(spotrac, "_scrape_team_with_retries", return_value=source):
            result = spotrac.scrape_contracts(["boston-celtics"])

        self.assertEqual(len(result.season_columns), 6)
        self.assertIn("2022-23", result.all_years.columns)
        self.assertNotIn("2022-23", result.displayed.columns)
        self.assertEqual(
            [column for column in result.displayed if column.startswith("20")],
            ["2023-24", "2024-25", "2025-26", "2026-27", "2027-28"],
        )
        self.assertEqual(result.displayed.iloc[0]["Player Key"], "test-player")

    def test_contract_scrape_rejects_empty_or_unknown_team_selection(self):
        with self.assertRaises(ValueError):
            spotrac.scrape_contracts([])
        with self.assertRaises(ValueError):
            spotrac.scrape_contracts(["not-an-nba-team"])

    def test_player_detail_service_rejects_non_spotrac_urls(self):
        with self.assertRaises(ValueError):
            spotrac.scrape_player_details(["http://localhost/internal"])

    def test_existing_player_scraper_defaults_remain_compatible(self):
        parsed = pd.DataFrame(
            [{"Player": "Test Player", "Player Link": "https://www.spotrac.com/player"}]
        )
        url = "https://www.spotrac.com/nba/player/_/id/12345/test-player"
        with (
            patch.object(spotrac.utils, "_save_page", return_value=BeautifulSoup("", "html.parser")),
            patch.object(
                spotrac,
                "_extract_player_details",
                side_effect=lambda _soup: parsed.copy(),
            ),
        ):
            legacy = spotrac.utils.scrape_player(url)
            app_record = spotrac.utils.scrape_player(url, detail_fields=["Country"])

        self.assertEqual(legacy.iloc[0]["Signed Using"], "NA")
        self.assertEqual(legacy.iloc[0]["Drafted"], "Undrafted")
        self.assertEqual(app_record.iloc[0]["Signed Using"], "")
        self.assertEqual(app_record.iloc[0]["Drafted"], "")
        self.assertEqual(app_record.iloc[0]["Country"], "")

    def test_player_detail_export_has_a_stable_schema(self):
        source = pd.DataFrame(
            [
                {
                    "Player": "Test Player",
                    "Player Link": "https://example.test/player",
                    "Player Key": "test-player",
                    "Signed Using": "UFA",
                    "Drafted": "",
                    "Country": "USA",
                }
            ]
        )
        player_url = "https://www.spotrac.com/nba/player/_/id/12345/test-player"
        with patch.object(spotrac, "scrape_players", return_value=source) as scrape:
            result = spotrac.scrape_player_details([f" {player_url} "])

        self.assertEqual(result.columns.tolist(), [*PLAYER_DETAIL_COLUMNS, "Data Source"])
        self.assertEqual(result.iloc[0]["Drafted"], "")
        self.assertEqual(result.iloc[0]["Country"], "USA")
        scrape.assert_called_once()
        self.assertEqual(scrape.call_args.args[0], [player_url])


class TestSportswsService(unittest.TestCase):
    def test_positions_scraper_parses_and_sorts_player_data(self):
        response = Mock()
        response.content = b"""
            <table><tbody>
              <tr><td><a href="/nba/z-player">Z Player</a>, BOS, F</td></tr>
              <tr><td><a href="/nba/a-player">A Player</a>, LAL, G</td></tr>
              <tr><td><a href="/nba/placeholder-player">Placeholder</a>, BOS, G</td></tr>
            </tbody></table>
        """
        with patch("dmcb.services.sportsws.requests.get", return_value=response):
            positions = sportsws.get_positions()

        self.assertEqual(positions["Player Key"].tolist(), ["a-player", "z-player"])
        self.assertEqual(positions["Position"].tolist(), ["G", "F"])
        self.assertEqual(positions["Data Source"].tolist(), ["Sports.ws", "Sports.ws"])

    def test_positions_scraper_returns_empty_frame_with_schema_when_no_players(self):
        response = Mock()
        response.content = b"<html><body>No player table</body></html>"
        with patch("dmcb.services.sportsws.requests.get", return_value=response):
            positions = sportsws.scrape_positions()

        self.assertEqual(
            positions.columns.tolist(),
            ["Name", "Player Link", "Player Key", "Position"],
        )
        self.assertTrue(positions.empty)

    def test_positions_scraper_reports_network_errors(self):
        with (
            patch(
                "dmcb.services.sportsws.requests.get",
                side_effect=requests.ConnectionError("network unavailable"),
            ),
            self.assertRaisesRegex(RuntimeError, "Could not fetch Sports.ws positions"),
        ):
            sportsws.scrape_positions()


class TestContractReconciliation(unittest.TestCase):
    def test_numeric_amounts_compare_equal_and_status_values_remain_distinct(self):
        spotrac_data = pd.DataFrame(
            [
                {
                    "Player": "One Player",
                    "Player Key": "one-player",
                    "Team": "Boston Celtics",
                    "2026-27": "$1,000,000",
                    "2027-28": "UFA",
                }
            ]
        )
        existing = pd.DataFrame(
            [
                {
                    "Player": "One Player",
                    "Player Key": "one-player",
                    "Team": "Boston Celtics",
                    "2026-27": "1000000",
                    "2027-28": "RFA",
                },
                {
                    "Player": "Unselected Player",
                    "Player Key": "unselected-player",
                    "Team": "Miami Heat",
                    "2026-27": "5",
                },
            ]
        )
        owners = pd.DataFrame(
            [{"Player": "One Player", "Player Key": "one-player", "Owner": "GM"}]
        )

        result = reconciliation.compare_contracts(
            spotrac_data, existing, owners, selected_teams=["boston-celtics"]
        )
        statuses = dict(zip(result["Season"], result["Status"]))
        self.assertEqual(statuses["2027-28"], "Changed")
        self.assertNotIn("2026-27", statuses)
        self.assertNotIn("Unchanged", result["Status"].tolist())
        self.assertNotIn("unselected-player", result["Player Key"].tolist())
        self.assertEqual(result["Owner Match"].tolist(), ["GM"])
        self.assertEqual(reconciliation.format_contract_value("$1,000,000"), "$1000000")

    def test_missing_and_unmatched_records_are_explicit(self):
        spotrac_data = pd.DataFrame(
            [{"Player": "New Player", "Player Key": "new-player", "2026-27": "$8"}]
        )
        existing = pd.DataFrame(
            [{"Player": "Old Player", "Player Key": "old-player", "2026-27": "$9"}]
        )
        result = reconciliation.compare_contracts(
            spotrac_data, existing, pd.DataFrame(columns=["Player Key", "Owner"])
        )

        statuses = dict(zip(result["Player Key"], result["Status"]))
        self.assertEqual(statuses["new-player"], "Signed")
        self.assertEqual(statuses["old-player"], "Waived")
        self.assertEqual(result["Owner Match"].tolist(), ["", ""])

    def test_comparison_classifies_missing_values_and_extensions(self):
        spotrac_data = pd.DataFrame(
            [
                {
                    "Player": "Extended Player",
                    "Player Key": "extended-player",
                    "2026-27": "$11",
                    "2027-28": "$12",
                },
                {
                    "Player": "Blank Player",
                    "Player Key": "blank-player",
                    "2026-27": "",
                },
                {
                    "Player": "Missing Spotrac",
                    "Player Key": "missing-spotrac",
                    "2026-27": "",
                },
            ]
        )
        existing = pd.DataFrame(
            [
                {
                    "Player": "Extended Player",
                    "Player Key": "extended-player",
                    "2026-27": "$10",
                    "2027-28": "",
                },
                {
                    "Player": "Blank Player",
                    "Player Key": "blank-player",
                    "2026-27": "",
                },
                {
                    "Player": "Missing Spotrac",
                    "Player Key": "missing-spotrac",
                    "2026-27": "$13",
                },
            ]
        )

        result = reconciliation.compare_contracts(
            spotrac_data, existing, pd.DataFrame(columns=["Player Key", "Owner"])
        )
        statuses = {
            (row["Player Key"], row["Season"]): row["Status"]
            for row in result.to_dict("records")
        }

        self.assertEqual(statuses[("extended-player", "2026-27")], "Changed")
        self.assertEqual(statuses[("extended-player", "2027-28")], "Extended")
        self.assertNotIn(("blank-player", "2026-27"), statuses)
        self.assertEqual(statuses[("missing-spotrac", "2026-27")], "Changed")
        self.assertNotIn("Unchanged", result["Status"].tolist())

    def test_comparison_keeps_oldest_five_seasons_and_sorts_by_key_then_season(self):
        seasons = [
            "2019-20",
            "2020-21",
            "2021-22",
            "2022-23",
            "2023-24",
            "2024-25",
            "2025-26",
        ]
        spotrac_data = pd.DataFrame(
            [
                {
                    "Player": "Z Player",
                    "Player Key": "z-player",
                    **{season: "$2" for season in seasons},
                },
                {
                    "Player": "A Player",
                    "Player Key": "a-player",
                    **{season: "$2" for season in seasons},
                },
            ]
        )
        existing = pd.DataFrame(
            [
                {
                    "Player": "Z Player",
                    "Player Key": "z-player",
                    **{season: "$1" for season in seasons},
                },
                {
                    "Player": "A Player",
                    "Player Key": "a-player",
                    **{season: "$1" for season in seasons},
                },
            ]
        )

        result = reconciliation.compare_contracts(
            spotrac_data, existing, pd.DataFrame(columns=["Player Key", "Owner"])
        )

        self.assertEqual(
            result["Season"].drop_duplicates().tolist(),
            seasons[:5],
        )
        self.assertEqual(
            result[["Player Key", "Season"]].values.tolist(),
            [
                [key, season]
                for key in ["a-player", "z-player"]
                for season in seasons[:5]
            ],
        )
        self.assertNotIn("Unchanged", result["Status"].tolist())

    def test_contract_comparison_ignores_older_seasons_outside_spotrac_projection(self):
        spotrac_data = pd.DataFrame(
            [{"Player": "Player", "Player Key": "player", "2026-27": "$11"}]
        )
        existing = pd.DataFrame(
            [
                {
                    "Player": "Player",
                    "Player Key": "player",
                    "2025-26": "$9",
                    "2026-27": "$10",
                }
            ]
        )
        result = reconciliation.compare_contracts(
            spotrac_data, existing, pd.DataFrame(columns=["Player Key", "Owner"])
        )
        self.assertEqual(result["Season"].tolist(), ["2026-27"])

    def test_duplicate_player_keys_are_flagged_as_ambiguous(self):
        spotrac_data = pd.DataFrame(
            [
                {"Player": "Duplicate", "Player Key": "duplicate", "2026-27": "$1"},
                {"Player": "Duplicate", "Player Key": "duplicate", "2026-27": "$2"},
            ]
        )
        result = reconciliation.compare_contracts(
            spotrac_data, pd.DataFrame(), pd.DataFrame()
        )
        self.assertEqual(result["Status"].tolist(), ["Ambiguous"])

    def test_write_plan_preserves_owner_skips_missing_and_appends_new_keys(self):
        headers = [
            "Player",
            "Player Link",
            "Player Key",
            "Team",
            "Team Link",
            "Position",
            "Age",
            "2026-27",
            "2027-28",
            "2028-29",
            "2029-30",
            "2030-31",
            "Owner",
        ]
        raw_sheet = [
            headers,
            [
                "Existing Player",
                "old-link",
                "existing-player",
                "Boston Celtics",
                "old-team-link",
                "G",
                "25",
                "$1000000",
                "$1500000",
                "",
                "",
                "",
                "Existing Owner",
            ],
        ]
        scraped = pd.DataFrame(
            [
                {
                    "Player": "Existing Player",
                    "Player Link": "old-link",
                    "Player Key": "existing-player",
                    "Team": "Boston Celtics",
                    "Team Link": "old-team-link",
                    "Position": "G",
                    "Age": "25",
                    "2026-27": "$1,000,000",
                    "2027-28": "$2,000,000",
                    "2028-29": "",
                },
                {
                    "Player": "New Player",
                    "Player Link": "new-link",
                    "Player Key": "new-player",
                    "Team": "Boston Celtics",
                    "Team Link": "team-link",
                    "Position": "F",
                    "Age": "22",
                    "2026-27": "$3,000,000",
                },
            ]
        )
        owners = pd.DataFrame(
            [
                {"Player Key": "existing-player", "Owner": "Existing Owner"},
                {"Player Key": "new-player", "Owner": "New Owner"},
            ]
        )

        plan = reconciliation.build_sheet_write_plan(scraped, raw_sheet, owners)

        self.assertEqual([(update.cell, update.value) for update in plan.updates], [("I2", "$2000000")])
        self.assertEqual(len(plan.append_rows), 1)
        self.assertEqual(plan.append_start_row, 3)
        self.assertEqual(plan.append_rows[0][12], "New Owner")
        self.assertEqual(plan.append_rows[0][7], "$3000000")

    def test_write_plan_reports_duplicate_sheet_keys_instead_of_guessing(self):
        headers = [
            "Player", "Player Link", "Player Key", "Team", "Team Link",
            "Position", "Age", "2026-27", "2027-28", "2028-29",
            "2029-30", "2030-31", "Owner",
        ]
        raw_sheet = [
            headers,
            ["Player", "", "same-player", "", "", "", "", "$1", "", "", "", "", "GM A"],
            ["Player", "", "same-player", "", "", "", "", "$2", "", "", "", "", "GM B"],
        ]
        scraped = pd.DataFrame(
            [{"Player": "Player", "Player Key": "same-player", "2026-27": "$3"}]
        )
        plan = reconciliation.build_sheet_write_plan(
            scraped, raw_sheet, pd.DataFrame(columns=["Player Key", "Owner"])
        )
        self.assertEqual(plan.updates, [])
        self.assertEqual(plan.ambiguous_keys, ["same-player"])

    def test_sheet_backup_is_a_timestamped_csv(self):
        with tempfile.TemporaryDirectory() as temporary:
            backup = sheets.GoogleSheetsService.save_backup(
                [["Player", "Owner"], ["Test Player", "GM"]], temporary
            )
            with backup.open(newline="", encoding="utf-8") as file:
                rows = list(csv.reader(file))

        self.assertEqual(rows[1], ["Test Player", "GM"])
        self.assertTrue(backup.name.startswith("contracts-"))
        self.assertEqual(backup.suffix, ".csv")

    def test_sheets_write_aborts_if_sheet_changed_after_preview(self):
        class Worksheet:
            def __init__(self):
                self.updated = False

            def get_all_values(self):
                return [["Player Key"], ["player"]]

            def batch_update(self, *_args, **_kwargs):
                self.updated = True

        class Manager:
            def __init__(self):
                self.sheet = Worksheet()

            def get_worksheet(self, _name):
                return self.sheet

        service = sheets.GoogleSheetsService.__new__(sheets.GoogleSheetsService)
        service.manager = Manager()
        plan = reconciliation.SheetWritePlan(
            updates=[reconciliation.CellUpdate("A2", "updated")]
        )

        with self.assertRaisesRegex(RuntimeError, "changed after the write preview"):
            service.apply_write_plan(plan, expected_sheet_values=[["Player Key"], ["old"]])
        self.assertFalse(service.manager.sheet.updated)

    def test_owned_tab_uses_confirmed_owner_and_player_columns(self):
        service = sheets.GoogleSheetsService.__new__(sheets.GoogleSheetsService)
        service.read_values = lambda _worksheet: [
            ["Owner", "Unused", "Unused", "Player"],
            ["GM", "", "", "Test Player"],
        ]
        owners = service.read_owners()
        self.assertEqual(owners.iloc[0]["Owner"], "GM")
        self.assertEqual(owners.iloc[0]["Player Key"], "test-player")


if __name__ == "__main__":
    unittest.main()
