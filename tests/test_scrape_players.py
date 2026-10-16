import os
import sys
import pandas as pd

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

from scripts.utils import scrape_team, scrape_players, make_title_case


def ask_team(team: str = "atlanta-hawks") -> str:
    return input(f"Enter team name (default: {team}): ") or team

def get_contracts(team: str) -> pd.DataFrame:
    return scrape_team(team)

def list_urls(df: pd.DataFrame) -> list[str]:
    return df["Player Link"].to_list()

def get_all_details(urls: list[str]) -> pd.DataFrame:
    return scrape_players(urls)

def format_signed(df: pd.DataFrame) -> pd.DataFrame:
    df["Signed Using"] = df["Signed Using"].apply(make_title_case)
    return df

def print_df(df: pd.DataFrame) -> None:
    print(f"Contract details: ")
    print(df)

def main():
    team_name = ask_team()
    team_contracts = get_contracts(team_name)
    player_urls = list_urls(team_contracts)
    contract_details = get_all_details(player_urls)
    formatted_details = format_signed(contract_details)
    print_df(formatted_details)


if __name__ == "__main__":
    main()
