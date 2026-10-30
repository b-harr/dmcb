from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


PLAYER_DETAIL_COLUMNS = [
    "Player",
    "Player Link",
    "Player Key",
    "Signed Using",
    "Drafted",
    "Country",
    "Contract Terms",
    "Age",
    "College",
    "Exp",
    "Agent(s)",
    "Free Agent",
]

CONTRACT_IDENTITY_COLUMNS = [
    "Player",
    "Player Link",
    "Player Key",
    "Team",
    "Team Link",
    "Position",
    "Age",
]

CONTRACT_SOURCE = "Spotrac"
OWNER_SOURCE = "Google Sheets: Owned"
STATS_SOURCE = "Basketball-Reference"
POSITIONS_SOURCE = "Sports.ws"


@dataclass(frozen=True)
class ContractScrapeResult:
    all_years: pd.DataFrame
    displayed: pd.DataFrame
    season_columns: tuple[str, ...] = ()


@dataclass(frozen=True)
class CellUpdate:
    cell: str
    value: str
    old_value: str = ""


@dataclass
class SheetWritePlan:
    updates: list[CellUpdate] = field(default_factory=list)
    append_rows: list[list[str]] = field(default_factory=list)
    append_start_row: int | None = None
    ambiguous_keys: list[str] = field(default_factory=list)

    @property
    def change_count(self) -> int:
        return len(self.updates) + sum(
            1 for row in self.append_rows for value in row if value
        )
