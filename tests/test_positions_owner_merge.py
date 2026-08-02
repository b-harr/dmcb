import pandas as pd

from scripts import get_positions


class DummyGoogleSheetsManager:
    def __init__(self):
        self.calls = []

    def read_data(self, sheet_name=None):
        self.calls.append(sheet_name)
        return [
            ["Player", "Player Link", "Player Key", "Owner"],
            ["LeBron James", "https://example.com/lebron", "lebron-james", "Lakers"],
        ]


def test_merge_owner_from_google_sheets_appends_owner(monkeypatch):
    monkeypatch.setattr(get_positions, "GoogleSheetsManager", DummyGoogleSheetsManager)

    df = pd.DataFrame(
        {
            "Name": ["LeBron James"],
            "Player Link": ["https://example.com/lebron"],
            "Player Key": ["lebron-james"],
            "Position": ["SF"],
        }
    )

    merged = get_positions.merge_owner_from_google_sheets(df, sheet_name="Contracts")

    assert list(merged.columns)[-1] == "Owner"
    assert merged.loc[0, "Owner"] == "Lakers"
