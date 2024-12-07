import os
import sys

# Get the root project directory (2 levels up from the current script)
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Append the base_dir to sys.path to ensure modules can be imported
sys.path.append(base_dir)

# Create the path for file
output_dir = "data"
output_file = "spotrac_contracts.csv"

# Ensure the output folder exists
os.makedirs(output_dir, exist_ok=True)

# Define the full file path for the CSV file
output_csv = os.path.join(output_dir, output_file)

from utils.scrape_spotrac import scrape_all_teams
from utils.text_formatter import make_player_key, make_title_case
from utils.google_sheets_manager import GoogleSheetsManager

def main(update_csv=True, update_sheets=False, sheet_name="Contracts"):
    df = scrape_all_teams()

    if df is not None:
        # Add a column to identify the team
        df["Player Key"] = df["Player"].apply(make_player_key)

        # Add the Team Link column
        df["Team Link"] = df["Team"].apply(lambda team: f"https://www.spotrac.com/nba/{team}/yearly")

        # Rename the 'Team' column using the make_title_case function
        df["Team"] = df["Team"].apply(make_title_case)

        # Sort the combined DataFrame by Player Key (to maintain a consistent order)
        df = df.sort_values(by="Player Key", ignore_index=True)
        
        # Reorder columns to ensure the data is in the correct order (Player, Player Link, Player Key, Team, etc.)
        column_order = ["Player", "Player Link", "Player Key", "Team", "Team Link", "Position", "Age"] + [col for col in df.columns if col.startswith("20")]
        df = df[column_order]

    if update_csv == True:
        df.to_csv(output_csv, mode="w", index=False, encoding="utf-8")

    if update_sheets == True:
        sheets_manager = GoogleSheetsManager()
        sheets_manager.write_data([df.columns.tolist()] + df.values.tolist(), sheet_name=sheet_name, start_cell="A1")

# Main execution block
if __name__ == "__main__":
    main(update_csv=True, update_sheets=False)
    print(__file__)  # Print the full path to the current file
    #print(os.path.basename(__file__))  # Print only the file name
