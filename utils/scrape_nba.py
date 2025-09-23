import pandas as pd
from nba_api.stats.endpoints import leaguedashplayerstats

def scrape_nba_totals(year=2025):
    """
    Scrape NBA player totals for a given season using the official NBA API.

    Args:
        year (int): The NBA season year, e.g., 2025 for 2024-25 season.

    Returns:
        pd.DataFrame: Raw player totals with NBA columns.
    """
    # NBA API expects season string like '2024-25' for 2024-25 season
    season_str = f"{year-1}-{str(year)[-2:]}"  # e.g., 2024-25

    # Fetch the league dash player stats
    stats = leaguedashplayerstats.LeagueDashPlayerStats(season=season_str)
    df = stats.get_data_frames()[0]

    # Remove rows with missing player names
    df = df.dropna(subset=["PLAYER_NAME"])

    # Rename columns to match your pipeline
    df.rename(columns={
        "PLAYER_NAME": "Player",
        "TEAM_ABBREVIATION": "Team",
        "GP": "G",
        "MIN": "MP",
        "PTS": "PTS",
        "REB": "TRB",
        "AST": "AST",
        "STL": "STL",
        "BLK": "BLK",
        "TO": "TOV",
        "PF": "PF"
    }, inplace=True)

    # Reorder columns (without Player Key)
    column_order = ["Player", "Team", "G", "MP", "PTS", "TRB", "AST", "STL", "BLK", "TOV", "PF"]
    df = df[column_order]

    return df

if __name__ == "__main__":
    stats = scrape_nba_totals(year=2025)
    print(stats.head())
