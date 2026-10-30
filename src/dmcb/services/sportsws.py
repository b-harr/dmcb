from __future__ import annotations

import logging

import pandas as pd
import requests
from bs4 import BeautifulSoup

from dmcb import utils
from dmcb.models.records import POSITIONS_SOURCE


def get_positions() -> pd.DataFrame:
    positions = scrape_positions()
    if positions.empty:
        raise RuntimeError("Sports.ws returned no player positions.")

    positions = positions.copy()
    positions["Data Source"] = POSITIONS_SOURCE
    return positions


def scrape_positions() -> pd.DataFrame:
    return _process_sportsws_data(_scrape_sportsws_stats())


def _scrape_sportsws_stats() -> pd.DataFrame:
    url = "https://sports.ws/nba/stats"
    try:
        response = requests.get(url, headers=utils.HEADERS, timeout=utils.TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as error:
        logging.error("Error fetching data from %s: %s", url, error)
        raise RuntimeError(
            f"Could not fetch Sports.ws positions from {url}: {error}"
        ) from error

    soup = BeautifulSoup(response.content, "html.parser")
    player_data = []
    for player in soup.select("td:first-child a"):
        name = player.get_text(strip=True)
        href = player.get("href")
        link = f"https://sports.ws{href}" if href else ""
        sibling = player.next_sibling
        tail = sibling.strip() if isinstance(sibling, str) else ""
        player_data.append({"Name": name, "Player Link": link, "Tail": tail})

    columns = ["Name", "Player Link", "Team", "Position"]
    if not player_data:
        return pd.DataFrame(columns=columns)

    frame = pd.DataFrame(player_data)
    frame[["Team", "Position"]] = frame["Tail"].str.extract(r",\s*([\w*]+),\s*(\w+)")
    frame = frame.drop(columns=["Tail"])
    frame = frame[frame["Name"].str.strip().ne(".")]
    frame = frame.dropna(subset=["Name"]).fillna("")
    return frame.reindex(columns=columns)


def _process_sportsws_data(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["Player Key"] = (
        frame["Player Link"]
        .str.replace("https://sports.ws/nba/", "", regex=False)
        .apply(utils.make_player_key)
    )
    columns = ["Name", "Player Link", "Player Key", "Position"]
    frame = frame[~frame["Player Key"].str.contains("placeholder", case=False, na=False)]
    return frame[columns].sort_values(by="Player Key").reset_index(drop=True)