from scripts.scrape_spotrac import scrape_all_teams
from utils.text_formatter import make_player_key, make_title_case
from utils.google_sheets_manager import GoogleSheetsManager

def main(update_csv=True, update_sheets=False, sheet_name="Contracts"):
    team_data = scrape_all_teams()

    if team_data is not None:
        # Add a column to identify the team
        team_data["Player Key"] = team_data["Player"].apply(make_player_key)

        # Add the Team Link column
        team_data["Team Link"] = team_data["Team"].apply(lambda team: f"https://www.spotrac.com/nba/{team}/yearly")

        # Rename the 'Team' column using the make_title_case function
        team_data["Team"] = team_data["Team"].apply(make_title_case)

        # Sort the combined DataFrame by Player Key (to maintain a consistent order)
        team_data = team_data.sort_values(by="Player Key", ignore_index=True)
        
        # Reorder columns to ensure the data is in the correct order (Player, Player Link, Player Key, Team, etc.)
        column_order = ["Player", "Player Link", "Player Key", "Team", "Team Link", "Position", "Age"] + [col for col in team_data.columns if col.startswith("20")]
        team_data = team_data[column_order]

    if update_csv == True:
        team_data.to_csv("data/spotrac_contracts.csv", mode="w", index=False, encoding="utf-8")

    if update_sheets == True:
        sheets_manager = GoogleSheetsManager()
        sheets_manager.write_data([team_data.columns.tolist()] + team_data.values.tolist(), sheet_name=sheet_name)

# Main execution block
if __name__ == "__main__":
    main(update_csv=True, update_sheets=False)
