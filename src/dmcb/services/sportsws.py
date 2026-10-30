from __future__ import annotations

import pandas as pd

from dmcb.models.records import POSITIONS_SOURCE
from scripts.utils import scrape_positions


def get_positions() -> pd.DataFrame:
    positions = scrape_positions()
    if positions.empty:
        raise RuntimeError("Sports.ws returned no player positions.")

    positions = positions.copy()
    positions["Data Source"] = POSITIONS_SOURCE
    return positions