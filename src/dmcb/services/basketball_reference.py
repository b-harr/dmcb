from __future__ import annotations

from datetime import date
from pathlib import Path
import re

import pandas as pd

from dmcb.models.records import STATS_SOURCE
from scripts.utils import make_player_key, scrape_bbref_stats


def latest_available_season(archive_directory: str = "data/archive/bbref") -> int:
    seasons = available_cached_seasons(archive_directory)
    today = date.today()
    current_season_end_year = today.year + 1 if today.month >= 7 else today.year
    return max([*seasons, current_season_end_year])


def get_stats(season_end_year: int) -> pd.DataFrame:
    if season_end_year < 1947:
        raise ValueError("Basketball-Reference season end year must be 1947 or later.")

    stats = scrape_bbref_stats(season_end_year)
    if stats.empty:
        raise RuntimeError(f"Basketball-Reference returned no stats for {season_end_year}.")

    stats = stats[stats["Player"].fillna("").ne("League Average")].copy()
    stats["Player Key"] = stats["Player"].fillna("").map(make_player_key)
    stats["Data Source"] = STATS_SOURCE
    return stats


def available_cached_seasons(archive_directory: str = "data/archive/bbref") -> list[int]:
    years = []
    for path in Path(archive_directory).glob("NBA_*_totals.csv"):
        match = re.match(r"NBA_(\d{4})_totals\.csv$", path.name)
        if match:
            years.append(int(match.group(1)))
    return sorted(set(years), reverse=True)