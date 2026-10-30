from __future__ import annotations

from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import logging
import re
import time
from urllib.parse import urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup

from dmcb.models.records import (
    CONTRACT_IDENTITY_COLUMNS,
    CONTRACT_SOURCE,
    ContractScrapeResult,
    PLAYER_DETAIL_COLUMNS,
)
from dmcb import utils

PLAYER_DETAIL_EXTRA_FIELDS = PLAYER_DETAIL_COLUMNS[5:]
MAX_RETRIES = 3
RETRY_DELAY = 5


def scrape_team(
    team: str,
    session: requests.Session | None = None,
    season_limit: int | None = 5,
) -> pd.DataFrame:
    url = f"https://www.spotrac.com/nba/{team}/yearly"
    soup = utils._save_page(url, f".cache/teams/{team}.html", session=session)
    if soup is None:
        raise RuntimeError(f"Could not fetch Spotrac contracts for team {team} from {url}.")

    tables = [
        table
        for table_id in ("dataTable-active", "dataTable-pending")
        if (table := soup.find("table", {"id": table_id})) is not None
    ]
    if not tables:
        raise ValueError(
            f"Spotrac contract tables were not found for team {team} at {url}."
        )

    first_table = tables[0]
    header_row = first_table.find("thead")
    if header_row is None:
        raise ValueError(
            f"Spotrac contract table is missing its header for team {team} at {url}."
        )
    headers = [header.get_text(strip=True) for header in header_row.find_all("th")]
    if not headers or not any(header.casefold().startswith("player") for header in headers):
        raise ValueError(
            f"Spotrac contract table is missing the Player header for team {team} "
            f"at {url}."
        )
    if not first_table.find("tbody"):
        raise ValueError(
            f"Spotrac contract table is missing its body for team {team} at {url}."
        )
    season_headers = [header for header in headers if header.startswith("20")]
    if season_limit is not None:
        season_headers = season_headers[:season_limit]

    try:
        data = [
            row
            for table in tables
            for row in _extract_team_contracts(table, season_limit=season_limit)
        ]
    except (IndexError, ValueError) as error:
        raise ValueError(
            f"Could not parse Spotrac contracts for team {team} at {url}: {error}"
        ) from error
    columns = ["Player", "Player Link", "Position", "Age", *season_headers]
    return pd.DataFrame(data, columns=columns)


def scrape_teams() -> pd.DataFrame:
    all_data = []
    failures = []

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(_scrape_team_with_retries, team): team
            for team in utils.TEAMS
        }
        for future in as_completed(futures):
            team = futures[future]
            try:
                frame = future.result()
                if frame is None or frame.empty:
                    failures.append(f"{team}: no data returned")
                    logging.error("%s returned no data", team)
                    continue
                frame["Team"] = team
                all_data.append(frame)
                logging.info("Finished %s", team)
            except Exception as error:
                logging.error("%s failed: %s", team, error)
                failures.append(f"{team}: {error}")

    if failures:
        raise RuntimeError("One or more teams failed to scrape: " + "; ".join(failures))
    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()


def scrape_player(
    url: str,
    detail_fields: list[str] | None = None,
) -> pd.DataFrame:
    player = "-".join(urlparse(url).path.rstrip("/").split("/")[-2:])
    soup = utils._save_page(url, f".cache/players/{player}.html")
    if soup is None:
        raise RuntimeError(f"Could not fetch Spotrac player details: {url}")

    data = _extract_player_details(soup)
    if data.empty or not data.iloc[0].get("Player"):
        raise ValueError(
            f"Could not parse Spotrac player details for {player or url}: "
            f"expected player identity in Person JSON-LD or the player profile at {url}."
        )
    data["Player Key"] = data["Player"].apply(utils.make_player_key)
    legacy_defaults = detail_fields is None
    if "Signed Using" not in data:
        data["Signed Using"] = ""
    if legacy_defaults:
        data["Signed Using"] = data["Signed Using"].replace("", "NA")
    if "Drafted" not in data:
        data["Drafted"] = "Undrafted" if legacy_defaults else ""
    columns = ["Player", "Player Link", "Player Key", "Signed Using", "Drafted"]
    if detail_fields:
        columns.extend(column for column in detail_fields if column not in columns)
    for column in columns:
        if column not in data:
            data[column] = ""
    return data[columns]


def scrape_players(
    urls: list[str],
    detail_fields: list[str] | None = None,
) -> pd.DataFrame:
    all_data = []
    failures = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(scrape_player, url, detail_fields): url
            for url in urls
        }
        for future in as_completed(futures):
            url = futures[future]
            try:
                frame = future.result()
                if not frame.empty:
                    all_data.append(frame)
                    logging.info("Finished %s", url)
                else:
                    failures.append(f"{url}: no data returned")
                    logging.error("%s returned no data", url)
            except Exception as error:
                logging.error("%s failed: %s", url, error)
                failures.append(f"{url}: {error}")

    if failures:
        raise RuntimeError("One or more players failed to scrape: " + "; ".join(failures))
    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()


def _extract_team_contracts(
    table: BeautifulSoup,
    season_limit: int | None = 5,
) -> list[list[str | None]]:
    data: list[list[str | None]] = []
    for row_number, row in enumerate(table.select("tbody tr"), start=1):
        cells = row.find_all("td")
        if not cells:
            continue
        player_cell = cells[0]
        player_link = player_cell.find("a")
        player = player_cell.get("data-export", "").strip()
        if not player and player_link:
            player = player_link.get_text(strip=True)
        if not player:
            raise ValueError(
                f"contract row {row_number} is missing the player name"
            )
        link = player_link["href"] if player_link else None
        position_age = player_cell.select_one("div.text-muted")
        if position_age is not None:
            match = re.search(r"\(([^,]+),\s*(\d+)\)", position_age.get_text(strip=True))
            position, age = match.groups() if match else (None, None)
            contract_cells = cells[1:]
        else:
            position = cells[1].get("data-export", "").strip() or None
            age = cells[2].get("data-export", "").strip() or None
            contract_cells = cells[3:]

        def get_contract_value(cell: BeautifulSoup) -> str | None:
            export_value = cell.get("data-export", "").strip() or None
            pill = cell.select_one(".pill-start")
            pill_value = pill.get_text(strip=True) if pill else None
            for status in ("UFA", "RFA", "Two-Way", "Exhibit 10", "Exhibit 9"):
                if pill_value and pill_value.startswith(status):
                    return status
            if export_value == "0":
                return "$0"
            if pill_value and pill_value.startswith("$"):
                return pill_value.replace(",", "")
            return None

        values = [get_contract_value(cell) for cell in contract_cells]
        if season_limit is not None:
            values = values[:season_limit]
        data.append([player, link, position, age, *values])
    return data


def _scrape_team_with_retries(
    team: str,
    season_limit: int | None = 5,
) -> pd.DataFrame | None:
    with requests.Session() as session:
        session.headers.update(utils.HEADERS)
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return scrape_team(team, session=session, season_limit=season_limit)
            except Exception as error:
                if isinstance(error, requests.HTTPError) and getattr(
                    error.response, "status_code", None
                ) == 403:
                    raise
                if attempt == MAX_RETRIES:
                    raise
                logging.warning(
                    "%s scrape failed (%s/%s), retrying: %s",
                    team,
                    attempt,
                    MAX_RETRIES,
                    error,
                )
                time.sleep(RETRY_DELAY)


def _extract_player_details(soup: BeautifulSoup) -> pd.DataFrame:
    details = {}
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            structured_data = json.loads(script.string or script.get_text())
        except json.JSONDecodeError:
            continue
        if structured_data.get("@type") == "Person":
            details["Player"] = structured_data.get("name")
            details["Player Link"] = structured_data.get("url")
            break

    profile = soup.select_one("#main article > div.row.m-0.mt-0.pb-3")
    if profile is not None:
        team_position = profile.select_one(".col-md-12.text-yellow.fw-bold span")
        if team_position is not None:
            team_link = team_position.find("a")
            if team_link is not None:
                team = team_link.get_text(strip=True)
                details["Team"] = team
                details["Position"] = team_position.get_text(
                    " ", strip=True
                ).replace(team, "", 1).strip(" ,")

        for label in profile.find_all("strong"):
            value = label.find_next_sibling("span")
            if value is not None:
                details[label.get_text(strip=True).rstrip(":")] = value.get_text(
                    " ", strip=True
                )

    table = soup.find("div", class_="contract-details")
    if table is not None:
        for label, value in zip(
            table.find_all("div", class_="label"),
            table.find_all("div", class_="value"),
        ):
            details[label.get_text(strip=True).rstrip(":")] = value.get_text(strip=True)
    return pd.DataFrame([details])


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
            executor.submit(_scrape_team_with_retries, team, None): team
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

    details = scrape_players(selected, detail_fields=PLAYER_DETAIL_EXTRA_FIELDS)
    for column in PLAYER_DETAIL_COLUMNS:
        if column not in details:
            details[column] = ""
    details = details.reindex(columns=PLAYER_DETAIL_COLUMNS)
    details["Data Source"] = CONTRACT_SOURCE
    return details