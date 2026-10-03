import os
import sys
import pandas as pd
import pytest


base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

import utils.spotrac_scraper as spotrac_scraper


def test_scrape_teams_fails_when_a_team_exhausts_retries(monkeypatch):
    monkeypatch.setattr(spotrac_scraper, "TEAMS", ["team-a", "team-b"])

    def scrape_team_with_retries(team, session):
        if team == "team-b":
            raise RuntimeError("exhausted retries")
        return pd.DataFrame({"Player": ["Player A"]})

    monkeypatch.setattr(
        spotrac_scraper,
        "scrape_team_with_retries",
        scrape_team_with_retries,
    )

    with pytest.raises(RuntimeError, match="team-b: exhausted retries"):
        spotrac_scraper.scrape_teams()
