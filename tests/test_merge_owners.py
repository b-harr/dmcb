import unittest
from unittest.mock import patch

import pandas as pd

from scripts.pull_contracts import merge_owners as merge_contract_owners
from dmcb.utils import merge_owners


class TestMergeOwners(unittest.TestCase):
    def test_conflicting_owners_are_not_assigned(self):
        contracts = pd.DataFrame(
            {
                "Player": ["Ambiguous Player", "Known Player"],
                "Player Key": ["ambiguous-player", "known-player"],
            }
        )
        owners = pd.DataFrame(
            {
                "Player Key": [
                    "ambiguous-player",
                    "ambiguous-player",
                    "known-player",
                ],
                "Owner": ["GM A", "GM B", "Known GM"],
            }
        )

        with (
            patch("dmcb.utils.pd.read_csv", return_value=owners),
            self.assertLogs("root", level="WARNING") as logs,
        ):
            result = merge_owners(contracts)

        self.assertEqual(result["Owner"].tolist(), ["", "Known GM"])
        self.assertIn("ambiguous-player", logs.output[0])

    def test_duplicate_rows_with_the_same_owner_are_not_ambiguous(self):
        contracts = pd.DataFrame(
            {"Player Key": ["same-player", "same-player"]}
        )
        owners = pd.DataFrame(
            {
                "Player Key": ["same-player", "same-player"],
                "Owner": ["Same GM", "Same GM"],
            }
        )

        with patch("dmcb.utils.pd.read_csv", return_value=owners):
            result = merge_owners(contracts)

        self.assertEqual(result["Owner"].tolist(), ["Same GM", "Same GM"])

    def test_contract_script_does_not_assign_conflicting_owners(self):
        contracts = pd.DataFrame({"Player Key": ["ambiguous-player"]})
        owners = pd.DataFrame(
            {
                "Player Key": ["ambiguous-player", "ambiguous-player"],
                "Owner": ["GM A", "GM B"],
            }
        )

        with self.assertLogs("root", level="WARNING") as logs:
            result = merge_contract_owners(contracts, owners)

        self.assertEqual(result["Owner"].tolist(), [""])
        self.assertIn("ambiguous-player", logs.output[0])


if __name__ == "__main__":
    unittest.main()
