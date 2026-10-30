from __future__ import annotations

from datetime import date
from pathlib import Path
import re

import pandas as pd

from dmcb import utils
from dmcb.models.records import STATS_SOURCE


def scrape_bbref_stats(year: int) -> pd.DataFrame:
    url = f"https://www.basketball-reference.com/leagues/NBA_{year}_totals.html"
    soup = utils._save_page(url, f".cache/stats/bbref-{year}.html")
    if soup is None:
        raise RuntimeError(f"Could not fetch Basketball-Reference stats for {year}.")

    table = soup.find("table", {"id": "totals_stats"})
    if not table:
        raise ValueError("Table not found. Ensure the page structure has not changed.")

    headers = [header.get_text() for header in table.find("thead").find_all("th")][1:]
    headers.extend(["Player Link", "Team Link"])
    rows = []
    for row in table.find("tbody").find_all("tr"):
        if not row.find("td"):
            continue
        values = [cell.get_text() for cell in row.find_all("td")]
        player_link, team_link = None, None
        for link in row.find_all("a"):
            href = link.get("href", "")
            if "/players/" in href:
                player_link = "https://www.basketball-reference.com" + href
            elif "/teams/" in href:
                team_link = "https://www.basketball-reference.com" + href
        rows.append([*values, player_link, team_link])
    return pd.DataFrame(rows, columns=headers)


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
        raise RuntimeError(
            f"Basketball-Reference returned no stats for {season_end_year}."
        )
    if "Player" not in stats.columns:
        raise ValueError(
            f"Basketball-Reference data for {season_end_year} is missing "
            "the Player column."
        )

    stats = stats[stats["Player"].fillna("").ne("League Average")].copy()
    stats["Player Key"] = stats["Player"].fillna("").map(utils.make_player_key)
    stats["Data Source"] = STATS_SOURCE
    return stats


def available_cached_seasons(archive_directory: str = "data/archive/bbref") -> list[int]:
    years = []
    for path in Path(archive_directory).glob("NBA_*_totals.csv"):
        match = re.match(r"NBA_(\d{4})_totals\.csv$", path.name)
        if match:
            years.append(int(match.group(1)))
    return sorted(set(years), reverse=True)