from __future__ import annotations

from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
from urllib.parse import urlparse

import pandas as pd

from dmcb.models.records import (
    CONTRACT_IDENTITY_COLUMNS,
    CONTRACT_SOURCE,
    ContractScrapeResult,
    PLAYER_DETAIL_COLUMNS,
)
from dmcb import utils

PLAYER_DETAIL_EXTRA_FIELDS = PLAYER_DETAIL_COLUMNS[5:]


def available_teams() -> list[str]:
    return sorted(utils.TEAMS)


def _season_sort_key(column: str) -> int:
    match = re.match(r"^(20\d{2})-\d{2}$", column)
    return int(match.group(1)) if match else -1


def scrape_contracts(teams: Iterable[str], display_seasons: int = 5) -> ContractScrapeResult:
    selected = list(dict.fromkeys(teams))
    if not selected:
        raise ValueError("Select at least one NBA team.")

    invalid = sorted(set(selected) - utils.TEAMS)
    if invalid:
        raise ValueError(f"Unknown NBA team slug(s): {', '.join(invalid)}")
    if display_seasons < 1:
        raise ValueError("display_seasons must be positive.")

    frames_by_team: dict[str, pd.DataFrame] = {}
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=min(6, len(selected))) as executor:
        futures = {
            executor.submit(utils._scrape_team_with_retries, team, None): team
            for team in selected
        }
        for future in as_completed(futures):
            team = futures[future]
            try:
                frame = future.result()
                if frame is None or frame.empty:
                    failures.append(f"{team}: Spotrac returned no contract data")
                    continue
                frame = frame.copy()
                frame["Player Key"] = frame["Player"].fillna("").map(utils.make_player_key)
                frame["Team"] = utils.make_title_case(team)
                frame["Team Link"] = f"https://www.spotrac.com/nba/{team}/yearly"
                frames_by_team[team] = frame
            except Exception as error:
                failures.append(f"{team}: {error}")
    if failures:
        raise RuntimeError("One or more Spotrac team requests failed: " + "; ".join(failures))

    frames = [frames_by_team[team] for team in selected]
    all_years = pd.concat(frames, ignore_index=True, sort=False)
    season_columns = tuple(
        sorted(
            (column for column in all_years.columns if re.match(r"^20\d{2}-\d{2}$", str(column))),
            key=_season_sort_key,
            reverse=True,
        )
    )
    all_years = all_years.reindex(columns=[*CONTRACT_IDENTITY_COLUMNS, *season_columns])
    all_years["Data Source"] = CONTRACT_SOURCE
    all_years = all_years.sort_values(["Player Key", "Team"], ignore_index=True)

    displayed_seasons = list(reversed(season_columns[:display_seasons]))
    display_columns = [*CONTRACT_IDENTITY_COLUMNS, *displayed_seasons]
    displayed = all_years.reindex(columns=display_columns).copy()
    displayed["Data Source"] = CONTRACT_SOURCE
    return ContractScrapeResult(all_years, displayed, season_columns)


def scrape_player_details(urls: Iterable[str]) -> pd.DataFrame:
    selected = list(dict.fromkeys(url.strip() for url in urls if url.strip()))
    if not selected:
        raise ValueError("Enter at least one Spotrac player URL.")
    for url in selected:
        parsed = urlparse(url)
        if (
            parsed.scheme not in {"http", "https"}
            or parsed.hostname not in {"spotrac.com", "www.spotrac.com"}
            or not parsed.path.startswith("/nba/player/")
        ):
            raise ValueError(f"Not a Spotrac NBA player URL: {url}")

    details = utils.scrape_players(selected, detail_fields=PLAYER_DETAIL_EXTRA_FIELDS)
    for column in PLAYER_DETAIL_COLUMNS:
        if column not in details:
            details[column] = ""
    details = details.reindex(columns=PLAYER_DETAIL_COLUMNS)
    details["Data Source"] = CONTRACT_SOURCE
    return details