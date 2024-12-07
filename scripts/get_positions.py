import os
import sys
import logging

# Get the root project directory (2 levels up from the current script)
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Append the base_dir to sys.path to ensure modules can be imported
sys.path.append(base_dir)

# Create the path for file
output_dir = "data"
output_file = "sportsws_positions.csv"

# Ensure the output folder exists
os.makedirs(output_dir, exist_ok=True)

# Define the full file path for the CSV file
output_csv = os.path.join(output_dir, output_file)

# Configure logging to capture detailed script execution and errors
logging.basicConfig(
    level=logging.INFO,  # Log messages with level INFO and above
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger()

# Log the script start with a timestamp to track execution
logger.info("The script started successfully.")

from utils.scrape_sportsws import scrape_sportsws_positions
from utils.text_formatter import make_player_key
from utils.google_sheets_manager import GoogleSheetsManager

def main(update_csv=True, update_sheets=False, sheet_name="Positions"):
    df = scrape_sportsws_positions()
    # Add a column to identify the team
    df["Player Key"] = df["Player Link"].str.replace("https://sports.ws/nba/", "").apply(make_player_key)

    # Sort the combined DataFrame by Player Key (to maintain a consistent order)
    df = df.sort_values(by="Player Key", ignore_index=True)
    
    # Reorder columns to ensure the data is in the correct order (Player, Player Link, Player Key, Team, etc.)
    column_order = ["Name", "Player Link", "Player Key", "Team", "Position"]
    df = df[column_order]

    if update_csv == True:
        df.to_csv(output_csv, mode="w", index=False, encoding="utf-8")

    if update_sheets == True:
        # Authenticate and update the Google Sheets with the processed data
        try:
            # Get the current timestamp to indicate when the data was last updated
            timestamp = logging.Formatter('%(asctime)s').format(logging.LogRecord("", 0, "", 0, "", [], None))  # Get the current timestamp
            
            # Initialize Google Sheets manager and clear existing data in the sheet
            sheets_manager = GoogleSheetsManager()
            sheets_manager.clear_data(sheet_name=sheet_name)
            logger.info(f"Cleared existing data in Google Sheets '{sheet_name}'.")

            # Write the timestamp to Google Sheets
            sheets_manager.write_data([[f"Last updated {timestamp} by {sheets_manager.service_account_email}"]], sheet_name=sheet_name, start_cell="A1")
            logger.info("Wrote timestamp to Google Sheets.")

            # Write the processed data to the 'Stats' sheet
            sheets_manager.write_data([df.columns.tolist()] + df.values.tolist(), sheet_name=sheet_name, start_cell="A2")
            logger.info(f"Data successfully written to the '{sheet_name}' sheet.")
        except Exception as e:
            logger.error(f"Error updating Google Sheets: {e}")

if __name__ == "__main__":
    main(update_csv=True, update_sheets=True)
    